import socket
from secure import get_cipher
from secure import get_plaintext
from time import time
import json


class Client:

    def __init__(self, ip, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((ip, port))

        self.clock_offset = self.get_clock_offset()

        print(f'connected to {ip} at {port}')

    def recv(self):
        cipher = self.socket.recv(1024)
        message = get_plaintext(cipher)


        return message

    def send(self, message):
        cipher = get_cipher(message)
        self.socket.sendall(cipher)

    
    def send_packet(self, packet, idx):
        packet['idx'] = idx
        packet['timestamp'] = time()

        jsonify = json.dumps(packet)

        cipher = get_cipher(jsonify)
        self.socket.sendall(cipher)

    def send_move(self, move, idx):
        jsonify = json.dumps({'movement': move, 'idx': idx})

        cipher = get_cipher(jsonify)
        self.socket.sendall(cipher)

        #print(f'message sent {jsonify}')


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

    def close(self):
        print('closing socket...')

        self.socket.close()
