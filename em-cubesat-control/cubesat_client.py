import socket,select,pickle

class CubeSatClient:
    def __init__(self,name,hostname,port=10000,debug=True):
        '''
        CubesatClient allows for communication with the master control and for actuation on the rpi zero

        name: string name of this unit
        host: hostname for master (ip address)
        port: port to connect to (set to same as master)
        '''

        self.name = name
        self.hostname = hostname
        self.port = port

        # Disable printing to stdout if not debug
        if not debug:
            sys.stdout = open(os.devnull, 'w')

    def connect_to_master(self):
        '''
        Blocking function call to establish a socket connection with master
        '''
        # Master expects a connectino followed by a message containing this unit's name
        self.sckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('Attempting to connect to master at %s'%self.hostname)
        self.sckt.connect((self.hostname,self.port))
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

    def __del__(self):
        self.sckt.close()


if __name__ == '__main__':
    c = CubeSatClient('test','192.168.0.13')
    c.connect_to_master()
    c.run()
