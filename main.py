import ezsp
import railtest

#zigbeeUart = '/dev/ttyUSB0'
zigbeeUart = 'COM10'
zwaveUart = 'COM4'

zigbee = ezsp.ZigbeeNcp(zigbeeUart, baudrate=57600, xonxoff=True, rtscts=False, timeout=5)
zwave = railtest.RailTest(zwaveUart, baudrate=115200, xonxoff=False, rtscts=False, timeout=5)

try:
    zigbee.mfgTest()
    print('Zigbee testing finished successfuly')
except Exception as e:
    print(e)
    print('Zigbee testing failed')
finally:
    print("Finish Zigbee testing")

try:
    zwave.testByCwWithoutSaw()
    print('Zwave testing finished successfuly')
except Exception as e:
    print(e)
    print('Zwave testing failed')
finally:
    print("Finish Zwave testing")