import socket, select, pickle, time
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

    def get_sensor_data(self,unit_idx,num_samples=1,rate=1):
        self.send_msg(unit_idx,Msg('read_sensor',(num_samples,rate)))
        samples = 0
        while samples < num_samples:
            try:
                msg = self.units[unit_idx].conn.recv(1024)
            except BlockingIOError:
                pass
            else:
                samples += 1
                if len(msg) == 0:
                    print('Client has shut down unexpectedly!')
                    return
                else:
                    msg = pickle.loads(msg)
                    print('Recieved data:',msg)

    def run_2_cube_test(self,t_repel,t_coast,t_attract,save_path=None,recv_buffer=0.25):
        total_time = t_repel+t_coast+t_attract
        data0 = []
        data1 = []
        self.send_msg(0,Msg('run_rotation',[(0,1,t_repel),(0,0,t_coast),(1,1,t_attract)]))
        self.send_msg(1,Msg('run_rotation',[(0,1,t_repel),(0,0,t_coast),(1,-1,t_attract)]))
        t0 = time.time()
        t = 0
        while t < total_time + recv_buffer:

            try:
                msg = self.units[0].conn.recv(1024)
            except BlockingIOError:
                pass
            else:
                if len(msg) == 0:
                    print('Client has shut down unexpectedly!')
                    return
                else:
                    data0.append(pickle.loads(msg))

            try:
                msg = self.units[1].conn.recv(1024)
            except BlockingIOError:
                pass
            else:
                if len(msg) == 0:
                    print('Client has shut down unexpectedly!')
                    return
                else:
                    data1.append(pickle.loads(msg))

            t = time.time() - t0

        if save_path is None:
            return data1
        else:
            i = 1
            while os.path.exists(save_path):
                (filename,extension) = os.path.splittext(save_path)
                save_path = '%s-%d.%s'%(filename,i,extension)
                i += 1
            

    def __del__(self):
        for u in self.units:
            u.conn.close()
        self.server.close()

if __name__ == '__main__':
    m = Master(num_units=3)
    m.connect_units()
    m.send_msg(0,Msg('echo',None))
