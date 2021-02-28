from bluepy.btle import DefaultDelegate, UUID, Peripheral, BTLEException, BTLEDisconnectError
import time
import struct
from collections import deque

service_uuid = UUID(0xDFB0)
serial_port_char_uuid = UUID(0xDFB1)


class DataPacket:
    def __init__(self, data):
        self.dancePosition = (data & (0b11 << 118)) >> 118
        self.danceState = (data & (0b1 << 114)) >> 114
        self.leftRight = (data & (0b11 << 112)) >> 112
        self.xAccel = decodeDataField((data & 0xFFFF000000000000000000000000) >> 96)
        self.yAccel = decodeDataField((data & 0xFFFF00000000000000000000) >> 80)
        self.zAccel = decodeDataField((data & 0xFFFF0000000000000000) >> 64)
        self.yaw = decodeDataField((data & 0xFFFF000000000000) >> 48)
        self.pitch = decodeDataField((data & 0xFFFF00000000) >> 32)
        self.row = decodeDataField((data & 0xFFFF0000) >> 16)
        self.CRC = getSignedInt((data & 0xFF00) >> 8, 8)


class MyDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleNotification(self, handle, data):
        packet = int.from_bytes(data, 'big')
        packetHex = hex(packet)

        if handshakeCompleted:
            bufferData(data)
        else:
            if isValidPacketBytes(packet) and isValidCommandPacket(packet):
                handleCommandPacket(packet)
            elif isValidPacketBytes(packet) and isValidDataPacket(packet):
                print("data packet received without handshake:", packetHex)
            elif isValidDataPacket(packet):
                print("unrecognised packet type:", packetHex)
            else:
                print("error packet:", packetHex)


buffer = deque()
packetBuilder = bytearray()


def bufferData(data):
    buffer.extend(data)  # add bytes to data buffer


def buildPacket():
    packetBuilderSpace = 16 - len(packetBuilder)  # calculates the space in packetBuilder left to build one packet

    if len(buffer) >= packetBuilderSpace:  # if enough bytes in buffer to fill packetBuilder
        for index in range(packetBuilderSpace):
            packetBuilder.append(buffer.popleft())  # add bytes to packetBuilder and take off packet

    if len(packetBuilder) == 16:  # this should always be true // packetBuilder is 'full'
        if packetBuilder[0] == 0xAC and packetBuilder[15] == 0xBE:  # valid packet, print and clear packetBuilder
            # print("packet formed:", packetBuilder)
            handleDataPacket(int.from_bytes(packetBuilder, 'big'))
            packetBuilder.clear()
        else:  # invalid packet built, find the next start byte
            packetBuilder.pop()  # remove the invalid start byte
            while len(packetBuilder) > 0 and packetBuilder[0] != 0xAC:
                packetBuilder.pop()


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


def getCommandBits(command):
    return {
        'ACK': 0,
        'NAK': 1,
        'hello': 2
    }.get(command, 7)


def handleDataPacket(packet):
    dancePositionMask = dancePosition << 118
    packet = packet | dancePositionMask  # set dance position bits
    decodedPacket = DataPacket(packet)
    # print("command packet:", hex(packet))
    print(decodedPacket.__dict__)


def handleCommandPacket(packet):
    global currentCommand
    commandByte = (packet & 0x00FF00) >> 8
    commandBits = (commandByte & 0b11100000) >> 5
    currentCommand = {
        0: 'ACK',
        1: 'NAK',
        2: 'hello'
    }.get(commandBits, 'error')
    print("command packet received:", currentCommand)


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


def scanAndConnect(address):
    global connected
    try:
        beetle.connect(address)
        print("connected")
        connected = True
    except BTLEException:
        print("unable to connect, attempting in 1s")
        time.sleep(1)


def handshake():
    global handshakeCompleted
    helloPacket = makeCommandPacket('hello')
    serial_port_char.write(helloPacket)  # say hello to beetle
    #  receive ACK from beetle
    try:
        beetle.waitForNotifications(5.0)  # try waiting this amount for ACK
    except BTLEDisconnectError:
        print("Disconnected attempting reconnection")
        scanAndConnect(mac_address)

    if currentCommand == 'ACK':
        ackPacket = makeCommandPacket('ACK')
        serial_port_char.write(ackPacket)
        print("handshake completed")
        handshakeCompleted = True
        return
    else:
        print("wrong response:", currentCommand, "sending hello again")
        handshake()
    print("timeout attempting handshake again")
    handshake()  # call handshake again due to timeout or wrong response


beetle = Peripheral()
beetle.setDelegate(MyDelegate())

mac_address = "80:30:DC:D9:1F:B2"
dancePosition = 1

connected = False  # only used once at the start to connect
currentCommand = 'None'  # tracks current command from beetle
handshakeCompleted = False

while not connected:
    scanAndConnect(mac_address)  # after this point it is definitely connected
#  gets handle and data
serial_port_service = beetle.getServiceByUUID(service_uuid)
serial_port_char = serial_port_service.getCharacteristics(serial_port_char_uuid)[0]
serial_port_handle = serial_port_char.getHandle()

handshake()
while True:
    try:
        beetle.waitForNotifications(1.0)
        buildPacket()
    except BTLEDisconnectError:
        print("Disconnected attempting reconnection")
        handshakeCompleted = False
        scanAndConnect(mac_address)
        handshake()
