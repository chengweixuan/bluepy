from bluepy.btle import DefaultDelegate, UUID, Peripheral, BTLEException, BTLEDisconnectError
import time
import struct
from collections import deque
import threading

service_uuid = UUID(0xDFB0)
serial_port_char_uuid = UUID(0xDFB1)


class DataPacket:
    def __init__(self, data):
        self.dancePosition = (data & (0b11 << 126)) >> 126
        self.danceState = (data & (0b1 << 122)) >> 122
        self.leftRight = (data & (0b11 << 120)) >> 120
        self.xAccel = decodeDataField((data & 0xFFFF00000000000000000000000000) >> 104)
        self.yAccel = decodeDataField((data & 0xFFFF0000000000000000000000) >> 88)
        self.zAccel = decodeDataField((data & 0xFFFF000000000000000000) >> 72)
        self.yaw = decodeDataField((data & 0xFFFF00000000000000) >> 56)
        self.pitch = decodeDataField((data & 0xFFFF0000000000) >> 40)
        self.row = decodeDataField((data & 0xFFFF000000) >> 24)
        self.EMG = decodeDataField((data & 0xFFFF00) >> 8)


class MyDelegate(DefaultDelegate):
    def __init__(self, index):
        DefaultDelegate.__init__(self)
        self.index = index

    def handleNotification(self, handle, data):
        # print(self.index, "received data")
        packet = int.from_bytes(data, 'big')
        packetHex = hex(packet)

        if handshakeCompletedFlags[self.index]:
            bufferData(data, self.index)
        else:
            if isValidPacketBytes(packet) and isValidCommandPacket(packet):
                handleCommandPacket(packet, self.index)
            elif isValidPacketBytes(packet) and isValidDataPacket(packet):
                print("data packet received without handshake:", packetHex)
            elif isValidDataPacket(packet):
                print("unrecognised packet type:", packetHex)
            else:
                print("error packet:", packetHex)


def bufferData(data, index):
    buffers[index].extend(data)  # add bytes to data buffer


def getSignedInt(number, bitSize):
    msb = number >> (bitSize - 1)

    if msb:  # is negative due to msb being 1, do inverse 2's complement
        int_max = 2 ** bitSize - 1
        complement = int_max + 1 - number
        complement = complement * -1
        return complement
    else:
        return number


def decodeDataField(field):
    flippedData = flipDataBytes(field)
    return getSignedInt(flippedData, 16)


def flipDataBytes(dataBytes):
    firstByte = (dataBytes & 0xFF00) >> 8
    secondByte = (dataBytes & 0xFF) << 8
    return firstByte + secondByte


def getMacAddressFromIndex(index):
    return {
        1: "80:30:DC:D9:1F:B2",  # test beetle
        2: "34:B1:F7:D2:37:5B",  # dance beetle
        3: "80:30:DC:E9:08:F4",  # naked beetle
        4: "80:30:DC:D9:0C:9D",  # zip-lock beetle
        5: "80:30:DC:D9:0C:FB",  # white beetle
        6: "80:30:DC:E9:25:55"  # emg beetle
    }.get(index, "invalid mac address")


def getCommandBits(command):
    return {
        'ACK': 0,
        'NAK': 1,
        'hello': 2
    }.get(command, 7)


def handleDataPacket(packet, index):
    dancePositionMask = (index + 1) << 118
    packet = packet | dancePositionMask  # set dance position bits
    decodedPacket = DataPacket(packet)
    if corrupted_packet(decodedPacket):
        return
    receivedPackets[index] = decodedPacket
    dataCounters[index] = dataCounters[index] + 1


def handleCommandPacket(packet, index):
    global currentCommands
    commandByte = (packet & 0x00FF00) >> 8
    commandBits = (commandByte & 0b11100000) >> 5
    currentCommands[index] = {
        0: 'ACK',
        1: 'NAK',
        2: 'hello'
    }.get(commandBits, 'error')
    print("command packet received:", currentCommands[index])


def isValidCommandPacket(packet):
    if len(hex(packet)) == 8:
        commandByte = (packet & 0x00FF00) >> 8
        checksum = commandByte & 0b11111
        if checksum == 0b01011:
            return True
    else:
        return False


def test(packet):
    if len(hex(packet)) == 8:
        commandByte = (packet & 0x00FF00) >> 8
        checksum = commandByte & 0b11111
        print(commandByte)
        print(checksum)


def isValidDataPacket(packet):
    if (len(hex(packet))) == 34:
        crcMask = 0xFF00
        packetCRC = (packet & crcMask) >> 8
        if isValidPacketCRC(packetCRC):
            return True
        else:
            return False


def isValidPacketCRC(packetCRC):  # settle CRC code
    return True


def isValidPacketBytes(packet):
    packet = int(packet)
    packetHexLength = len(hex(packet)) - 2
    startByteMask = 15 * (16 ** (packetHexLength - 1)) + 15 * (16 ** (packetHexLength - 2))
    startByte = (packet & startByteMask) >> ((packetHexLength - 2) * 4)
    endByte = packet & 0xFF
    if (startByte == 0xAC) and (endByte == 0xBE):
        return True
    else:
        return False


def makeCommandPacket(command):
    checksum = 0b01011
    shiftedCommandBits = (getCommandBits(command) << 5)
    commandByte = shiftedCommandBits + checksum
    return struct.pack('>B', commandByte)


def isInvalidIndexRange(index):
    if index > 6 or index < 1:
        return True
    else:
        return False


def oob(angle):
    return angle > 180 or angle < -180


def corrupted_packet(decodedPacket):
    return oob(decodedPacket.yaw) and oob(decodedPacket.pitch) and oob(decodedPacket.row)


class PrintPackets(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.allConnected = False

    def run(self):
        while True:
            if handshakeCompletedFlags[0] and handshakeCompletedFlags[1] and handshakeCompletedFlags[2]:
                self.allConnected = True

            if handshakeCompletedFlags[0] and handshakeCompletedFlags[1] and handshakeCompletedFlags[2]:
                for index in range(len(receivedPackets)):
                    print(index, dataCounters[index], receivedPackets[index].__dict__)
                print()  # provides space

            elif self.allConnected:
                disconnected_beetles = "Error: beetle: "
                for index in range(len(receivedPackets)):
                    if not handshakeCompletedFlags[index]:
                        disconnected_beetles += str(index) + " "
                disconnected_beetles += "are disconnected"
                print(disconnected_beetles)
                time.sleep(1)

            time.sleep(0.05)  # test delay to limit print


class BeetleThread(threading.Thread):
    def __init__(self, index):
        threading.Thread.__init__(self)
        self.index = index
        self.beetle = Peripheral()

        self.connected = False

    def scanAndConnect(self):
        mac_address = mac_addresses[self.index]
        try:
            self.beetle.connect(mac_address)
            print(self.index, "connected")
            self.connected = True
        except BTLEException:
            print(self.index, "unable to connect, attempting in 1s")
            time.sleep(1)

    def handshake(self, serial_port_char):
        helloPacket = makeCommandPacket('hello')
        serial_port_char.write(helloPacket)  # hello to beetle
        try:
            self.beetle.waitForNotifications(5.0)
        except BTLEDisconnectError:
            print(self.index, "Disconnected attempting reconnection")
            self.scanAndConnect()

        if currentCommands[self.index] == 'ACK':
            ackPacket = makeCommandPacket('ACK')
            serial_port_char.write(ackPacket)
            print(self.index, "handshake completed")
            handshakeCompletedFlags[self.index] = True
            # currentCommands[self.index] = 'none'
            return
        else:
            print(self.index, "wrong response:", currentCommands[self.index], "sending hello again")
            time.sleep(1)
            self.handshake(serial_port_char)
        print(self.index, "timeout attempting handshake again")
        self.handshake(serial_port_char)

    def buildPacket(self):
        if len(packetBuilders[self.index]) == 0 and len(buffers[self.index]) == 0:
            return

        builderSpace = 17 - len(packetBuilders[self.index])

        if len(buffers[self.index]) >= builderSpace:
            for index in range(builderSpace):
                leftByte = buffers[self.index].popleft()
                packetBuilders[self.index].append(leftByte)

        if len(packetBuilders[self.index]) == 17:
            if packetBuilders[self.index][0] == 0xAC and packetBuilders[self.index][16] == 0xBE:
                handleDataPacket(int.from_bytes(packetBuilders[self.index], 'big'), self.index)
                packetBuilders[self.index].clear()
            else:
                packetBuilders[self.index].pop()
                while len(packetBuilders[self.index]) > 0 and packetBuilders[self.index][0] != 0xAC:
                    packetBuilders[self.index].pop()

    def run(self):
        self.beetle.setDelegate(MyDelegate(self.index))

        while not self.connected:
            self.scanAndConnect()

        serial_port_service = self.beetle.getServiceByUUID(service_uuid)
        serial_port_char = serial_port_service.getCharacteristics(serial_port_char_uuid)[0]

        self.handshake(serial_port_char)  # complete handshake

        while True:
            try:
                self.beetle.waitForNotifications(0.5)
            except BTLEDisconnectError:
                print(self.index, "disconnected during transfer attempting reconnection")
                handshakeCompletedFlags[self.index] = False
                self.scanAndConnect()
                buffers[self.index].clear()
                packetBuilders[self.index].clear()
                self.handshake(serial_port_char)
                currentCommands[self.index] = 'none'

            self.buildPacket()


mac_addresses = ["", "", ""]
beetles_used = ["", "", ""]
correctInput = False
mac_address_indexes = "1: Test beetle \n" \
                      "2: Black beetle \n" \
                      "3: Yellow beetle \n" \
                      "4: Teal beetle \n" \
                      "5: White beetle \n" \
                      "6: EMG beetle \n"

while not correctInput:
    print(mac_address_indexes)
    print("Input the beetles according the dancer positions 1-3 from left to right")
    firstDancer = int(input("Enter beetle MAC address index of the first dancer: "))
    secondDancer = int(input("Enter beetle MAC address index of the second dancer: "))
    thirdDancer = int(input("Enter beetle MAC address index of the dancer dancer: "))

    if isInvalidIndexRange(firstDancer) or isInvalidIndexRange(secondDancer) or isInvalidIndexRange(thirdDancer):
        print("Invalid index entered. Try again")
    else:
        mac_addresses[0] = getMacAddressFromIndex(firstDancer)
        mac_addresses[1] = getMacAddressFromIndex(secondDancer)
        mac_addresses[2] = getMacAddressFromIndex(thirdDancer)
        correctInput = True


currentCommands = ['none', 'none', 'none']
buffers = [deque(), deque(), deque()]
packetBuilders = [bytearray(), bytearray(), bytearray()]
handshakeCompletedFlags = [False, False, False]
receivedPackets = [DataPacket(0), DataPacket(0), DataPacket(0)]
dataCounters = [0, 0, 0]

for beetleIndex in range(3):
    thread = BeetleThread(beetleIndex)
    thread.start()

printThread = PrintPackets()
printThread.start()
