import socket,select,pickle,os
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

        # Setup GPIO
        self.em_pins = [(26,19),(13,6)]

        GPIO.setmode(GPIO.BCM)
        for pins in self.em_pins:
            GPIO.setup(pins[0],GPIO.OUT)
            GPIO.setup(pins[1],GPIO.OUT)
            GPIO.output(pins[0],0)
            GPIO.output(pins[1],0)

        # PWM frequency
        self.pwm_frequency = pwm_frequency


    def connect_to_master(self):
        '''
        Blocking function call to establish a socket connection with master
        '''
        # Master expects a connection followed by a message containing this unit's name
        self.sckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('Attempting to connect to master at %s'%self.master_hostname)
        self.sckt.connect((self.master_hostname,self.port))
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
            p = GPIO.PWM(pin,self.pwm_frequency)
            p.start(intensity*100)
        elif msg.msg_type == 'power_em':
            print('Message is power_em')
            em_idx = msg.data[0]
            intensity = msg.data[1]

    def __del__(self):
        self.sckt.close()
        GPIO.cleanup()

if __name__ == '__main__':
    c = CubeSatClient(master_hostname='192.168.0.13')
    c.connect_to_master()
    c.run()
