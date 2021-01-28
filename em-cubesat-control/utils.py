class Msg:
    '''
    Send this message from master to client to control EM output, tests etc
    '''
    def __init__(self,msg_type='echo',data=[]):
        msg_types = ['echo','power_em','read_sensor','run_rotation','run_full_test']
        if msg_type not in msg_types:
            raise Exception("Undefined msg_type. Must be one of: %s"%msg_types)

        self.msg_type = msg_type
        self.data = data

class Unit:
    def __init__(self,name,conn):
        '''
        Each unit should have a unique name (str) and a socket connection
        '''
        self.name = name
        self.conn = conn
