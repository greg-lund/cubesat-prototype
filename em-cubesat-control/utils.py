class Msg:
    '''
    Send this message from master to client to control EM output, tests etc
    '''
    def __init__(self,msg_type='echo',data=[]):
        '''
        ---------------------------------------------
        Overview of message types:
        ---------------------------------------------
        echo: a message used to test socket connection
            - data should be of type string
            - client should simply echo data back to master
        gpio_pwm: a message used to test pwm on a specific gpio pin (BCM-based indexing)
            - data should be a tupe (or list): (gpio_pin,intensity)
                - gpio_pin should be a non-reserved, available pin and intensity float in range [0,1]
        power_em: a message to power a specific em with a specific intensity
            - data should be a tuple (or list): (em_id,intensity)
                - em_id int in range [0,3], intensity float in range [-1,1]
        read_sensor: a message to send sensor reading back to master
            - TODO
        run_rotation: a message to initiate a single rotation
            - TODO
        run_full_test: a message to initiate a full scale test
            - TODO
        '''
        msg_types = ['echo','gpio_pwm','power_em','read_sensor','run_rotation','run_full_test']
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
