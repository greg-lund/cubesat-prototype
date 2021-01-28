import socket, select, pickle
import sys, os
from utils import *

class Master:
    def __init__(self,num_units=1,hostname=socket.gethostname(),port=10000,debug=True):

        # How many cubesat units will be used in this test (and should be connected to)
        self.num_units = num_units

        # Disable printing to stdout if not debug
        if not debug:
            sys.stdout = open(os.devnull, 'w')

        # Setup server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((hostname,port))
        self.server.listen(5)

        # Store all of the socket connections
        self.units = []

    def connect_units(self):
        '''
        Blocking function call to connect to all num_units cubesats
        '''
        print('Attempting to connect to %d units...'%self.num_units)

        while len(self.units) < self.num_units:

            conns,_,_ = select.select([self.server],[],[])
            for s in conns:
                # Only look at new connections
                if s is self.server:
                    # On connection we expect to get a message with our unit's name
                    conn,addr = self.server.accept()
                    data = conn.recv(1024)
                    conn.setblocking(False)
                    print('Connected to %s at %s'%(data.decode(),addr[0]))
                    self.units.append(Unit(data.decode(),conn))

        print('Connected to all units')
        self.server.setblocking(False)

    def send_msg(self,unit_idx,msg):
        if unit_idx >= len(self.units):
            print('unit_idx out of range')
            return
        self.units[unit_idx].conn.sendall(pickle.dumps(msg))

    def __del__(self):
        for u in self.units:
            u.conn.close()
        self.server.close()

if __name__ == '__main__':
    m = Master(num_units=3)
    m.connect_units()
    m.send_msg(0,Msg('echo',None))
