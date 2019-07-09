import serial
import time

class RailTest:
    def __init__(self, portname, baudrate=115200, xonxoff=False, rtscts=False, timeout=10):
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

        self.EOL = '\r\n'

    def __del__(self):
        if self.port != None:
            self.port.close()

    def __sendCommand(self, command, *args):
        outputString = ''

        outputString += command

        for arg in args:
            outputString += ' ' + arg
        
        outputString += self.EOL

        self.port.flushInput()
        self.port.write(outputString)

        return outputString


    def rx(self, state):
        self.__sendCommand('rx', str(state))
    
    def setZwaveMode(self, val1, val2):
        self.__sendCommand('SetZwaveMode', str(val1), str(val2))

    def setTxLength(self, value):
        self.__sendCommand('SetTxLength', str(value))

    def setTxPayload(self, val1, val2):
        self.__sendCommand('SetTxPayload', str(val1), str(val2))

    def setZwaveRegion(self, value):
        self.__sendCommand('SetZwaveRegion', str(value))

    def setPower(self, power, ptype):
        self.__sendCommand('SetPower', str(power), ptype)

    def setChannel(self, channel):
        self.__sendCommand(str(channel))
    
    def setTxTone(self, state):
        self.__sendCommand('setTxTone', state)

    def testByCwWithoutSaw(self, region=0, powerValue=0, powerType='raw' channel=1, timeout=10):
        self.rx(0)
        self.setZwaveMode(1, 3)
        self.setTxLength(20)
        self.setTxPayload(7, 20)
        self.setZwaveRegion(region)
        self.setPower(powerValue, powerType)
        self.setChannel(channel)

        self.setTxTone(1)
        time.sleep(timeout)
        self.setTxTone(0)


        