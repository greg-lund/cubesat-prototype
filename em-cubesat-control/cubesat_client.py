import socket,select,pickle,os,time,sys
from utils import *
import RPi.GPIO as GPIO

class CubeSatClient:
    def __init__(self,master_hostname='gregs-macbook',port=10000,pwm_frequency=1000,debug=True,use_sensors=False):
        '''
        CubesatClient allows for communication with the master control and for actuation on the rpi zero

        master_hostname: hostname for master (or ip address)
        port: port to connect to (set to same as master)
        '''

        # Socket connection parameters
        self.name = os.getenv('USER')
        self.master_hostname = master_hostname
        self.port = port

        # Disable printing to stdout if debug is off
        if not debug:
            sys.stdout = open(os.devnull, 'w')

        # PWM frequency
        self.pwm_frequency = pwm_frequency

        # Setup em GPIO
        self.em_pins = [(19,26),(6,13),(27,22),(4,17)]
        self.setup_ems()

        # Setup corner ems
        self.corner_pins = [(14,15),(18,23),(24,25),(10,9)]
        self.setup_corner_ems()

        # Setup sensors
        self.use_sensors = use_sensors
        if self.use_sensors:
            import board,busio,adafruit_vl6180x
            self.sensor_shutdown_pins = [4,17,27,22]
            self.sensors = []
            self.connect_sensors()
            print('Connected to %d sensors!'%len(self.sensors))

    def setup_ems(self):
        '''
        Setup em gpio pins for pwm
        '''
        # Store pwm instances
        self.em_pwm = []

        # Use GPIO numbering scheme
        GPIO.setmode(GPIO.BCM)
        for pins in self.em_pins:
            # Setup output pins
            GPIO.setup(pins[0],GPIO.OUT)
            GPIO.setup(pins[1],GPIO.OUT)
            GPIO.output(pins[0],0)
            GPIO.output(pins[1],0)

            # Create PWM instances for our output pins
            self.em_pwm.append((GPIO.PWM(pins[0],self.pwm_frequency),GPIO.PWM(pins[1],self.pwm_frequency)))

    def setup_corner_ems(self):

        self.corner_pwm = []

        for pins in self.corner_pins:
            GPIO.setup(pins[0],GPIO.OUT)
            GPIO.setup(pins[1],GPIO.OUT)
            GPIO.output(pins[0],0)
            GPIO.output(pins[1],0)
            self.corner_pwm.append((GPIO.PWM(pins[0],self.pwm_frequency),GPIO.PWM(pins[1],self.pwm_frequency)))

    def power_corner_em(self,em_idx,intensity):

        if em_idx > len(self.corner_pwm):
            print('ERROR: em_idx in msg is greater than number of active corner ems')
            return
        if intensity < -1 or intensity > 1:
            print('ERROR: intensity in msg is out of range [-1,1]')
            return

        in1 = self.corner_pwm[em_idx][0]
        in2 = self.corner_pwm[em_idx][1]

        if intensity <= 0:
            in1.start(100)
            in2.start(100*(1+intensity))
        else:
            in2.start(100);
            in1.start(100*(1-intensity))

    def connect_sensors(self):
        '''
        Attempt to connect to all available ToF sensors
        '''
        # Initialize i2c interface
        self.i2c = busio.I2C(board.SCL,board.SDA)

        # Disable all sensors
        for pin in self.sensor_shutdown_pins:
            GPIO.setup(pin,GPIO.OUT)
            GPIO.output(pin,0)

        # Enable a single sensor at a time and connect
        addr = 20
        for pin in self.sensor_shutdown_pins:
            GPIO.output(pin,1)
            if 0x29 in self.i2c.scan():
                s = adafruit_vl6180x.VL6180X(self.i2c,0x29)
                s._write_8(0x0212,addr)
                del s
                self.sensors.append(adafruit_vl6180x.VL6180X(self.i2c,addr))
                # Change some registers to get higher sample rate
                self.sensors[-1]._write_8(0x01B, 0x00) # SYSRANGE_INTRAMEASUREMENT_PERIOD = 10ms
                self.sensors[-1]._write_8(0x01C, 0x05) # SYSRANGE_MAX_CONVERGENCE_TIME = 5ms
                self.sensors[-1]._write_8(0x10A, 0x18) # READOUT_AVERAGE_SAMPLE_PERIOD = 2.65ms

                addr+=1

    def test_gpio(self):
        '''
        Test GPIO pins. Note: this should only be done with em_pins connected to leds or some other small load.
        Don't run this while the h-bridges and electromagnets are connected!
        '''
        for pins in self.em_pins:
            for pin in pins:
                p = GPIO.PWM(pin,self.pwm_frequency)
                p.start(0)
                for dc in range(1,101):
                    p.ChangeDutyCycle(dc)
                    time.sleep(0.01)
                for dc in range(100,-1,-1):
                    p.ChangeDutyCycle(dc)
                    time.sleep(0.01)
                p.stop()
                GPIO.output(pin,0)

    def connect_to_master(self,connect_attempts=5,retry_time=1):
        '''
        Blocking function call to establish a socket connection with master
        '''
        # Master expects a connection followed by a message containing this unit's name
        self.sckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('Attempting to connect to master at %s'%self.master_hostname)
        for i in range(connect_attempts):
            try:
                self.sckt.connect((self.master_hostname,self.port))
            except socket.error:
                if i == connect_attempts-1:
                    print('Failed to connect after %d attempts, aborting!'%connect_attempts)
                    return False
                print('Unable to connect to master. Retrying in %d seconds'%retry_time)
                time.sleep(retry_time)
            else:
                break
        self.sckt.sendall(self.name.encode())
        self.sckt.setblocking(False)
        print('Connected!')
        return True

    def startup(self):
        connected = False
        while True:
            if not connected:
                connected = self.connect_to_master(1,1)
                time.sleep(1)
                continue
            
            try:
                msg = self.sckt.recv(1024)
            except socket.error:
                pass
            else:
                if len(msg) == 0:
                    connected = False
                    continue
                msg = pickle.loads(msg)
                self.act_msg(msg)

    def run(self):
        '''
        Main loop for client
        '''
        while True:
            try:
                msg = self.sckt.recv(1024)
            except socket.error:
                pass
            else:
                if len(msg) == 0:
                    print('Master has shut down, exiting...')
                    quit()
                else:
                    print('Recieved a message from master!')
                    msg = pickle.loads(msg)
                    self.act_msg(msg)


    def act_msg(self,msg):
        '''
        Act on incoming message from master
        '''

        if msg is None:
            print("Message is None!")
            return

        if msg.msg_type == 'echo':
            print('Message is echo, echoing back to master...')
            self.sckt.sendall(msg.data.encode())

        elif msg.msg_type == 'gpio_pwm':
            pin = msg.data[0]
            intensity = msg.data[1]
            print('Message is gpio_pwm. Starting pwm on gpio %d at %f%% intensity.'%(pin,100*intensity))

        elif msg.msg_type == 'power_em':
            print('Message is power_em')

            em_idx = msg.data[0]
            intensity = msg.data[1]

            self.power_em(em_idx,intensity)

        elif msg.msg_type == 'read_sensor':
            print('Message is read sensor')

            # If no msg data included, just send one sensor reading
            if msg.data is None or len(msg.data) == 0:
                reading = self.get_sensor_reading()
                reading.insert(0,0) # Set time to zero
                self.sckt.sendall(pickle.dumps(reading))
            else:
                num_samples = msg.data[0]
                dt = 1.0/msg.data[1]
                t0 = time.time()
                for _ in range(num_samples):
                    s = time.time()
                    t = s - t0
                    reading = self.get_sensor_reading()
                    reading.insert(0,t)
                    self.sckt.sendall(pickle.dumps(reading))
                    leftover = dt - (time.time()-s)
                    if leftover > 0:
                        time.sleep(leftover)

        elif msg.msg_type == 'run_rotation':
            print('Message is run_rotation')

            samples = 0
            t_start = time.time()
            t = 0
            t0 = time.time()
            for data in msg.data:
                em_idx = data[0]
                intensity = data[1]
                duration = data[2]

                if self.use_sensors:
                    sensor_data = [255 for _ in range(len(self.sensors)+1)]
                    self.start_continuous_sampling(em_idx)

                self.power_em(em_idx,intensity)
                t = time.time()-t0
                while t < duration:
                    # Get sensor reading from face we're powering
                    if self.use_sensors:
                        d = self.get_continuous_sample(em_idx)
                        sensor_data[em_idx+1] = d
                        sensor_data[0] = t
                        self.sckt.sendall(pickle.dumps(sensor_data))
                    samples += 1
                    t = time.time()-t0

                self.power_em(em_idx,0)
                if self.use_sensors:
                    self.end_continuous_sampling(em_idx)

    def get_sensor_reading(self):
        '''
        Return a list with each sensor reading
        '''
        reading = []
        for s in self.sensors:
            reading.append(s.range)
        return reading

    def power_em(self,em_idx,intensity):
        '''
        Power em_idx with given intensity
        '''

        if em_idx > len(self.em_pwm):
            print('ERROR: em_idx in msg is greater than number of active ems')
            return
        if intensity < -1 or intensity > 1:
            print('ERROR: intensity in msg is out of range [-1,1]')
            return

        in1 = self.em_pwm[em_idx][0]
        in2 = self.em_pwm[em_idx][1]

        if intensity <= 0:
            in1.start(100)
            in2.start(100*(1+intensity))
        else:
            in2.start(100);
            in1.start(100*(1-intensity))


    def start_continuous_sampling(self,sensor_idx):
        '''
        Start continuous sampling on a single tof sensor
        '''
        self.sensors[sensor_idx]._write_8(0x18,0x03)

    def end_continuous_sampling(self,sensor_idx):
        '''
        End continuous sampling on a single tof sensor
        '''
        self.sensors[sensor_idx]._write_8(0x018,0x01)
        
    def get_continuous_sample(self,sensor_idx):
        '''
        Get a single sample from a single tof sensor
        '''
        status = self.sensors[sensor_idx]._read_8(0x04f) & 0x07
        while status != 0x04:
            status = self.sensors[sensor_idx]._read_8(0x04f) & 0x07
        r = self.sensors[sensor_idx]._read_8(0x062)
        self.sensors[sensor_idx]._write_8(0x015,0x07)
        return r

    def continuous_rate_test(self,sensor_idx=0,N=100):
        '''
        Check the rate of continuous sensor reading on tof sensor
        '''
        s = self.sensors[sensor_idx]

        s._write_8(0x018,0x03) # Start range measurements
        t0 = time.time()
        for _ in range(N):
            status = s._read_8(0x04f) & 0x07 # Poll for new sample
            while status != 0x04:
                status = s._read_8(0x04f) & 0x07

            r = s._read_8(0x062) # Read range sample
            s._write_8(0x015,0x07) # Clear interrupt
        t1 = time.time()
        s._write_8(0x18,0x01) # Stop ranging
        return 1.0*N / (t1-t0)
    
    def single_shot_rate_test(self,sensor_idx=0,N=100):
        '''
        Check the rate of single-shot sensor reading on tof sensor
        '''
        s = self.sensors[0]
        t0 = time.time()
        for _ in range(N):
            r = s.range
        t1 = time.time()
        return 1.0*N / (t1-t0)

    def __del__(self):
        self.sckt.close()
        GPIO.cleanup()

if __name__ == '__main__':
    c = CubeSatClient(master_hostname='gregs-macbook',debug=False)
    c.startup()
