import socket, select, pickle
import sys, os

class Unit:
    def __init__(self,name,connection):
        '''
        Each unit should have a unique name (str) and a socket connection
        '''
        self.name = name
        self.connection = connection

class Master:
    def __init__(self,num_units=1,hostname=socket.gethostname(),port=10000,debug=True):

        # How many cubesat units will be used in this test (and should be connected to)
        self.num_units = num_units

        # Disable printing to stdout if not debug
        if not debug:
            sys.stdout = open(os.devnull, 'w')

        # Setup server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((hostname,port))
        self.server.setblocking(False)
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
                # Skip already connected units
                new = True
                for u in self.units:
                    if u.conn == conn: new = False
                if not new: continue

                # On connection we expect to get a message with our unit's name
                conn,addr = self.server.accept()
                conn.setblocking(False)
                data = conn.recv(1024)
                print('Connected to %s at %s!'%(data.decode(),addr[0]))
                self.units.append(Unit(data.decode(),conn))

        print('Connected to all units!')

    def __del__(self):
        for u in self.units:
            u.conn.close()
        self.server.close()



if __name__ == '__main__':
    m = Master(num_units=2)
    m.connect_units()
