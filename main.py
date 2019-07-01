import ezsp

#zigbeeUart = '/dev/ttyUSB0'
zigbeeUart = 'COM4'

zigbee = ezsp.ZigbeeNcp(zigbeeUart, baudrate=57600, xonxoff=True, rtscts=False, timeout=5)
try:
    zigbee.mfgTest()
except Exception as e:
    print(e)
finally:
    print("Finish testing")
