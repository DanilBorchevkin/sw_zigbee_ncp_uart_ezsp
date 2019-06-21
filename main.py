import ezsp

#zigbeeUart = '/dev/ttyUSB0'
zigbeeUart = 'COM10'

zigbee = ezsp.ZigbeeNcp(zigbeeUart)
zigbee.mfgTest()