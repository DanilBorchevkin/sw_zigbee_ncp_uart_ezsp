import time
import serial
import binascii

class NumberIterator:
    def __init__(self, limit, startValue = 0):
        self.limit = limit
        self.startValue = startValue
        self.reset()

    def __iter__(self):
        return self

    def next(self):
        if self.counter < self.limit:
            self.counter += 1
        else:
            self.counter = self.startValue
        return self.counter & 0xFF

    def reset(self):
        self.counter = self.startValue - 1
       
class ZigbeeNcp:
    
    def __init__(self, portname, baudrate=57600, xonxoff=True, rtscts=False, timeout=10):
        self.portname = portname
        self.timeout = timeout
        self.port = None
        try:
            self.port = serial.Serial(port=self.portname,
                                        baudrate=baudrate,
                                        bytesize=serial.EIGHTBITS,
                                        parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE,
                                        timeout=timeout,
                                        xonxoff=xonxoff,
                                        rtscts=rtscts,
                                        dsrdtr=False)

        except Exception as e:
            raise e

        self.ezspVersion = None
        self.ackNum = NumberIterator(7, startValue=1)
        self.frmNum = NumberIterator(7, startValue=1)
        self.sequenceNum = NumberIterator(255, startValue=0)

        self.RSTACK_FRAME_CMD = b'\x1A\xC0\x38\xBC\x7E'
        self.RSTACK_FRAME_ACK = b'\x1A\xC1\x02\x0B\x0A\x52\x7E'
        self.V4_EZSPCONF_FRAME_CMD = b'\x00\x42\x21\xA8\x50\xED\x2C\x7E'
        self.V5_EZSPCONF_FRAME_CMD = b'\x00\x42\x21\xA8\x51\xFD\x0D\x7E'
        self.V6_EZSPCONF_FRAME_CMD = b'\x00\x42\x21\xA8\x52\xCD\x6E\x7E'
        self.MFGLIB_START_ID = b'\x83'
        self.MFGLIB_END_ID = b'\x84'
        self.MFGLIB_SET_CHANNEL_ID = b'\x8A'
        self.MFGLIB_GET_CHANNEL_ID = b'\x8B'
        self.MFGLIB_SET_POWER_ID = b'\x8c'
        self.MFGLIB_GET_POWER_ID = b'\x8d'
        self.MFGLIB_START_TONE_ID = b'\x85'
        self.MFGLIB_STOP_TONE_ID = b'\x86'
        self.MFGLIB_START_STREAM_ID = b'\x87'
        self.MFGLIB_STOP_STREAM_ID = b'\x88'
        self.MFGLIB_SEND_PACKET_ID = b'\x88'
        self.FLAG_BYTE = b'\x7E'
        self.RANDOMIZE_START =  0x42
        self.RANDOMIZE_SEQ = 0xB8

    def __del__(self):
        if self.port != None:
            self.port.close()
        
    def debugOut(self, type, arr):
        data = ''.join(format(x, '02x') for x in arr)
        print('[' + type + '] ' + data) 

    def __dataRandomization(self, data):
        rand = self.RANDOMIZE_START
        out = bytearray()
        for c in data:
            out += bytearray([c ^ rand])
            if rand % 2:
                rand = (rand >> 1) ^ self.RANDOMIZE_SEQ
            else:
                rand = rand >> 1
        return out

    def __getControlByte(self, ackNum, frmNum):
        controlByte = (((ackNum << 0) & 0xFF) | ((frmNum << 4 ) & 0xFF)) & 0xFF
        result = bytearray([controlByte])
        return result

    def __appendCrc(self, data):
        crc = 0x1021

        msb = 0xFF
        lsb = 0xFF

        for c in data:
            x = c ^ msb
            x ^= (x >> 4)
            msb = (lsb ^ (x >> 3) ^ (x << 4)) & 255
            lsb = (x ^ (x << 5)) & 255
    
        return data + bytearray([msb]) + bytearray([lsb])
            
    def __appendFlag(self, data):
        result = data + self.FLAG_BYTE
        return result

    def __ashFrameBuilder(self, command):
        frame = bytearray()
        datafield = bytearray()
        # Control byte
        frame += self.__getControlByte(self.ackNum.next(), self.frmNum.next())
        
        # Sequence byte
        datafield += bytearray([self.sequenceNum.next()])
        # Frame control TODO fix this in future versions
        datafield += b'\x00'
        if self.ezspVersion >=5:
            # Legacy frame ID - always 0xFF
            datafield += b'\xFF'
            # Extended frame control
            datafield += b'\x00'
        datafield = datafield + command
        datafield = self.__dataRandomization(datafield)
        
        frame += datafield
        frame = self.__appendCrc(frame)
        frame = self.__replaceReservedBytes(frame)
        frame = self.__appendFlag(frame)
        return frame

    def __byteStuffing(self, data):
        result = data

        result = result.replace(b'\x7d\x5d', b'\x7d')
        result = result.replace(b'\x7d\x5e', b'\x7e')
        result = result.replace(b'\x7d\x31', b'\x11')
        result = result.replace(b'\x7d\x33', b'\x13')
        result = result.replace(b'\x7d\x38', b'\x18')
        result = result.replace(b'\x7d\x3a', b'\x1a')
        
        return result

    def __replaceReservedBytes(self, data, isContainFlagByte = False):
        result = data

        if isContainFlagByte:
            result = result[:-1]
        
        result = result.replace(b'\x7d', b'\x7d\x5d')
        result = result.replace(b'\x7e', b'\x7d\x5e')
        result = result.replace(b'\x11', b'\x7d\x31')
        result = result.replace(b'\x13', b'\x7d\x33')
        result = result.replace(b'\x18', b'\x7d\x38')
        result = result.replace(b'\x1a', b'\x7d\x3a')

        if isContainFlagByte:
            result += self.FLAG_BYTE

        return result

    def __getResponse(self, applyRandomize = False):
        timeout = int(time.time()) + self.timeout
        msg = bytearray()

        receivedbyte = None

        while ((int(time.time()) < timeout) and (receivedbyte != self.FLAG_BYTE)):
            receivedbyte = self.port.read()
            msg += receivedbyte

        if msg == bytearray():
            raise Exception('No response')

        msg = self.__byteStuffing(msg)
        self.debugOut('raw RESPONSE', msg)

        if applyRandomize:
            msg_parsed = self.__dataRandomization(bytearray(msg[1:-3]))
            self.debugOut('RESPONSE datafield', msg_parsed)
        return msg

    def sendResetFrame(self):
        self.port.flushInput()
        # EZSP RST Frame
        self.debugOut('send RESET FRAME', self.RSTACK_FRAME_CMD)
        self.port.write(self.RSTACK_FRAME_CMD)
        # Wait fpr RSTACK FRAME (Reset ACK)
        response = self.__getResponse()

        if response != bytearray(self.RSTACK_FRAME_ACK):
            raise Exception('Wrong Reset stack frame')
    
    def sendAck(self, response):
        ackNum = response[0]

        # Some tricky moment. some time isntead byte value we get int already
        # TODO fix this in future versions
        try:
            ackNum = int(ackNum.encode('hex'), 16)
        except:
            pass

        ack = bytearray([ackNum & 0x07 | 0x80])
        ack = self.__appendCrc(ack)
        ack = self.__replaceReservedBytes(ack)
        ack = self.__appendFlag(ack)
        
        self.debugOut('send ACK', ack)
        self.port.write(ack)

    def sendCommand(self, commandId,  commandName = '', applyRandomize = False):
        frame = self.__ashFrameBuilder(commandId)
        self.debugOut('send ' + commandName, frame)
        self.port.flushInput()
        self.port.write(frame)
        response = self.__getResponse(applyRandomize)
        self.sendAck(response)

    def sendVersion(self):
        # TODO refactoring this and merge with sendCommand
        frame = self.__ashFrameBuilder(b'\x00' + bytearray([self.ezspVersion]))
        self.debugOut('SEND VERSION', frame)
        self.port.flushInput()
        self.port.write(frame)
        response = self.__getResponse()
        self.sendAck(response)

    def v6init(self):

        # EZSP Configuration Frame: version ID: 0x00
        # Note: Must be sent before any other EZSP commands
        # { FRAME CTR + EZSP [0x00 0x00 0x00 0x06] + CRC + FRAME END }
        self.port.write(self.V6_EZSPCONF_FRAME_CMD)
        self.debugOut('write v6 init', self.V6_EZSPCONF_FRAME_CMD)

        # Wait for Data Response { protocolVersion, stackType, stackVersion }
        # this must be ACK'd
        response = self.__getResponse()

        # DATA ACK response frame
        self.sendAck(response)
        
        # Check ncp data response:
        # At this time we only checked first byte
        # TODO fix this shit
        if (response[0] == 0x01):
            return True
        else:
            return False

    def init(self):
        if self.ezspVersion == 6:
            self.v6init()
        else:
            raise Exception('No supported EZSP protocol found')

    def getProtocolVersion(self):
        self.ezspVersion = None 

        self.sendResetFrame()
        if self.v6init():
            self.ezspVersion = 6
            return    
        
    def testMfgTone(self, timeout=10):
        self.sendCommand(self.MFGLIB_START_ID, 'MFGLIB_START')
        self.sendCommand(self.MFGLIB_SET_CHANNEL_ID + b'\x14', 'MFGLIB_SET_CHANNEL')
        self.sendCommand(self.MFGLIB_SET_POWER_ID + b'\x00\x00\x03', 'MFGLIB_SET_POWER')
        # self.sendCommand(self.MFGLIB_GET_POWER_ID, 'MFGLIB_GET_POWER')

        self.sendCommand(self.MFGLIB_START_TONE_ID, 'MFGLIB_START_TONE')

        time.sleep(timeout)

        self.sendCommand(self.MFGLIB_STOP_TONE_ID, 'MFGLIB_END_TONE')
        self.sendCommand(self.MFGLIB_END_ID, 'MFGLIB_END')

    def testMfgStream(self, timeout = 10):
        self.sendCommand(self.MFGLIB_START_ID, 'MFGLIB_START')
        self.sendCommand(self.MFGLIB_START_STREAM_ID, 'MFGLIB_START_STREAM')

        time.sleep(timeout)

        self.sendCommand(self.MFGLIB_STOP_STREAM_ID, 'MFGLIB_STOP_STREAM')
        self.sendCommand(self.MFGLIB_END_ID, 'MFGLIB_END')
       
    def mfgTest(self):
        try:
            self.getProtocolVersion()

            if self.ezspVersion != None:
                self.debugOut('Detected protocol version', bytearray([self.ezspVersion]))
            else:
                raise Exception('No valid or acceptable version of EZSP protocol')
            
            self.testMfgTone(timeout=10)

        except Exception as e:
            raise e

        return True
