from bluepy.btle import DefaultDelegate, UUID, Peripheral, BTLEException, BTLEDisconnectError
import time
import struct

service_uuid = UUID(0xDFB0)
serial_port_char_uuid = UUID(0xDFB1)


class MyDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleNotification(self, handle, data):
        packet = int.from_bytes(data, 'big')
        packetHex = hex(packet)

        if isValidPacketBytes(packet):
            # has valid start and end bytes
            if isValidCommandPacket(packet):
                # handle command
                handleCommandPacket(packet)
                print("command packet:", packetHex)
            elif isValidDataPacket(packet):
                # store data
                handleDataPacket(packet)
                # print("data packet:", packetHex)
            else:
                print("unrecognised packet type:", packetHex)
        else:
            # handle error packet
            with open('siyin.txt', 'a') as f:
                f.write(f'error packet: {packetHex}\n')


def getMacAddressFromIndex(index):
    return {
        1: "80:30:DC:D9:1F:B2",  # test beetle
        2: "34:B1:F7:D2:37:5B",  # dance beetle
        3: "80:30:DC:E9:08:F4",  # naked beetle
        4: "80:30:DC:D9:0C:9D"  # zip-lock beetle
    }.get(index, "invalid mac address")


def getCommandBits(command):
    return {
        'ACK': 0,
        'NAK': 1,
        'hello': 2
    }.get(command, 7)


def handleDataPacket(packet):
    dancePositionMask = dancePosition << 118
    packet = packet | dancePositionMask  # set dance position bits
    print("command packet:", hex(packet))
    # with open('siying.txt', 'a') as f:
    #     f.write(f'command packet:{hex(packet)}\n')


def handleCommandPacket(packet):
    global currentCommand
    commandByte = (packet & 0x00FF00) >> 8
    commandBits = (commandByte & 0b11100000) >> 5
    currentCommand = {
        0: 'ACK',
        1: 'NAK',
        2: 'hello'
    }.get(commandBits, 'error')


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
    if (startByte == 0x7E) and (endByte == 0x7E):
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
        return
    else:
        print("wrong response:", currentCommand, "sending hello again")
        handshake()
    print("timeout attempting handshake again")
    handshake()  # call handshake again due to timeout or wrong response


beetle = Peripheral()
beetle.setDelegate(MyDelegate())

correctInput = False
connected = False
currentCommand = 'None'  # tracks current command from beetle
mac_address = "unknown"

while not correctInput:
    mac_address_index = int(input("Enter bluno beetle MAC address index: "))
    dancePosition = int(input("Enter user dance position: "))
    mac_address = getMacAddressFromIndex(mac_address_index)
    if mac_address_index > 5 or mac_address_index < 1 or dancePosition < 1 or dancePosition > 3:
        print("invalid index entered. Try again")
    else:
        mac_address = getMacAddressFromIndex(mac_address_index)
        correctInput = True

print("attempting connection to:", mac_address)

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
    except BTLEDisconnectError:
        print("Disconnected attempting reconnection")
        scanAndConnect(mac_address)
        handshake()

    # print("waiting for notifications")
