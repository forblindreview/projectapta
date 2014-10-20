#!/usr/bin/env python
import controller
import time
import zmq

import TangibleEvents

from DeviceProxy import *

class RotateEventListener(TangibleEvents.EventListener):
    def handleEvent(self, event):
        print "source: ", event.source, " value: ", event.value

def main():
    control = controller.DeviceController()
    
    ctx = zmq.Context(2,2,zmq.NOBLOCK)
    sock = zmq.Socket(ctx, zmq.REQ)
    
    sock.connect('tcp://127.0.0.1:10777')
    
    dev_list_reply = requestDevicesList(sock)
    dev_list = dev_list_reply[2]
    print dev_list_reply
    dev_list =  dev_list_reply[2]
    len = dev_list.__len__() - 1
    
    control.addDevice('powermate11')
    
    device_ref = control.getDevice('powermate11')
    control.addDevice('/dev/ttyUSB0.HR1')
    haptic_rotor = control.getDevice('/dev/ttyUSB0.HR1')
    
    print_listener = RotateEventListener()
    
    device_ref.addListener(TangibleEvents.ROTATE, print_listener)
    haptic_rotor.addListener(TangibleEvents.ROTATE, print_listener)
    control.start()
    
    #print 'about to sleep'
    try:
        while 1:
            time.sleep(0.001)
    except KeyboardInterrupt:
        print 'exiting now...'
        control.quit()
        time.sleep(1)
    #print 'naptime is over'
        #control.quit()
    
if __name__ == '__main__':
    main()