import struct
import time
from collections import deque

class LeftRightManager():
    def __init__(self):
        self.lock_duration = 10
        self.current_velocity = 0
        self.prev_velocity = 0
        self.velocity_decay = 0

    def computeLeftRight(self, current_velocity, prev_velocity):
        if self.lock_duration > 0:
            self.lock_duration = self.lock_duration - 1
            return 0
        elif prev_velocity > 0 and current_velocity < 0:
            #self.print_left()    
            self.lock_duration = 5
            return 1
        elif prev_velocity < 0 and current_velocity > 0:
            #self.print_right()
            self.lock_duration = 5
            return 2
        return 0

    def getDirection(self, raw_data):
        reading, alpha = 0, 0.5
        for j in range(0, 20):
            reading += (raw_data[j][2] / 1000)
        current_velocity = int(reading - self.velocity_decay)
        direction = self.computeLeftRight(current_velocity, self.prev_velocity) # 0 idle, 1 left, 2 right
        self.prev_velocity = current_velocity
        self.velocity_decay = self.velocity_decay * (1 - alpha) + alpha * reading
        return direction

    def print_left(self):
        print('''
 _        _______  _______ _________      _            
( \      (  ____ \(  ____ \\__   __/     / )           
| (      | (    \/| (    \/   ) (       / /            
| |      | (__    | (__       | |      / /_____  _____ 
| |      |  __)   |  __)      | |     ( ((_____)(_____)
| |      | (      | (         | |      \ \             
| (____/\| (____/\| )         | |       \ \            
(_______/(_______/|/          )_(        \_)           
                                                       
                                    ''')
    
    def print_right(self):
        print('''
 _______ _________ _______          _________              _    
(  ____ )\__   __/(  ____ \|\     /|\__   __/             ( \   
| (    )|   ) (   | (    \/| )   ( |   ) (                 \ \  
| (____)|   | |   | |      | (___) |   | |      _____  _____\ \ 
|     __)   | |   | | ____ |  ___  |   | |     (_____)(_____)) )
| (\ (      | |   | | \_  )| (   ) |   | |                  / / 
| ) \ \_____) (___| (___) || )   ( |   | |                 / /  
|/   \__/\_______/(_______)|/     \|   )_(                (_/   

                                    ''')
