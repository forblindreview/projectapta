#!/usr/bin/python
"""
This module defines classes for converting TouchOSC control surface messages into
Apta UI Toolkit events and commands. I'm writing this to remove the requirement of ZeroMQ 
for programming interaction applications with Apta UI Toolkit.
author: Anonymous Researcher <uumrz@clrmail.com>
"""
import sys
import time
from TangibleEvents import Event, EventListener
from touchOSCInputBridge import *


class rotateListener(EventListener):
    def handleEvent(self, event):
        print 'event on %s with value %f'%(event.handle, event.value)
 
def main(args):
    #Parse command-line arguments to set the hostname+port on which to
    # receive OSC messages
    parser = optparse.OptionParser("usage: %prog -H arg1 -P arg2")
    parser.add_option('-H', dest='hostname', default='127.0.0.1', type='string')
    parser.add_option('-P', dest='portnum', default=9000, type='int')
    #TODO add options for setting host, port for touchOSC device
    options, args = parser.parse_args()
    hostname = options.hostname
    portnum = options.portnum    
    #creates an OSC server that listens on port passed via cmd-line arguments
    oscServer = OSC.OSCServer((hostname, portnum))

    # TouchOSCInteractorProxy defines a method to handle OSC messages.
    # This method currently calls TouchOSCInteractorProxy.dispatchEvent, which 
    # instantiates a TangibleEvents.Event object and triggers that event on the 
    # appropriate control object. 
    ixProxy  = TouchOSCInteractorProxy()
    
    # Control elements within a TouchOSC layout are referenced by their class and
    # instance ID for a particular layout. So the 1st dial on a page is rotary1.
    # One drawback of this design is that it disposes of information about which
    # tab an interface element is laid out. One remedy is to consider tab change
    # events which are sent by touchOSC.
    for r in ['rotary1', 'rotary2', 'rotary3']:
        # Add a control with the handle in 'r' to your interactive context or
        # logical interface layout
        ixProxy.addDevice(r)
        # Get a reference to a controller.ContinuousControl object on which you
        # can define event driven behavior
        ix = ixProxy.getDevice(r)
        if ix is not None:
            ix.addListener(TangibleEvents.ROTATE, rotateListener())
    
    # This tells the OSC server to forward all OSC message and call
    # touchOSCHandlers.handleOSCMessage
    oscServer.addMsgHandler('default', ixProxy.handleOSCMessage)

    # start the OSCServer in another thread
    serverThread = threading.Thread(target=oscServer.serve_forever)
    serverThread.start()
    
    # Wait forever or until user wants to quit 
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        oscServer.close()
        sys.exit(0)

if __name__ == '__main__':
    main(sys.argv)
