from node import Client
from time import time
from time import sleep
import threading
from queue import Queue
from traceback import format_exc
from framingInput1 import beetle_thread


send_queue = Queue()

lock = threading.Lock()


class Laptop(Client):
    def __init__(self, ip, port):
        super(Laptop, self).__init__(ip, port)

        self.clock_offset = self.get_clock_offset()

        print(f'clock sync completed...clock offset is {self.clock_offset}s')

        self.sender_thread = threading.Thread(target=self.send_data)
        self.sender_thread.start()
        self.dancer = threading.Thread(target=beetle_thread())
        self.dancer.start()

    def get_clock_offset(self):
        print('starting clock offset calculation...')

        timestamp1 = time()

        self.send(str(timestamp1))

        timestamp2, timestamp3 = self.recv().split('|')
        timestamp2 = float(timestamp2)
        timestamp3 = float(timestamp3)
        timestamp4 = time()
        rtt = ((timestamp4 - timestamp1) - (timestamp3 - timestamp2)) / 2.0

        print(f'round-trip time = {rtt}')

        clock_offset = timestamp4 - int(timestamp3) - rtt

        return clock_offset

    def send_data(self):
        Y = input('Please enter Y when ready to send data: ')

        while Y:
            sleep(10)
            global send_queue

            try:
                lock.acquire()

                data = send_queue.get(block=False)
                if data:
                    timestamp = time()
                    delay = timestamp - self.clock_offset
                    message = '1|' + str(data) + '|' + str(delay)
                    self.send(message)
            except:
                print(f'an error occurred {format_exc()}')
                self.close()
                break
            finally:
                lock.release()
