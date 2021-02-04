import socket,select,pickle,os,time
from utils import *
import RPi.GPIO as GPIO

class CubeSatClient:
    def __init__(self,master_hostname,port=10000,pwm_frequency=500,debug=True):
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

        # Setup GPIO
        self.em_pins = [(26,19),(13,6)]
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
                    quit()
                print('Unable to connect to master. Retrying in %d seconds'%retry_time)
                time.sleep(retry_time)
            else:
                break
        self.sckt.sendall(self.name.encode())
        self.sckt.setblocking(False)
        print('Connected!')

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

    def __del__(self):
        self.sckt.close()
        GPIO.cleanup()

if __name__ == '__main__':
    c = CubeSatClient(master_hostname='192.168.0.13')
    c.connect_to_master()
    c.run()
