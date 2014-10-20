#!/usr/bin/env python
"""
This module contains an input bridge from touchOSC/iOS control surfaces to 
applications built with Apta UI Toolkit. This version is 'one to throw away', as future 
versions would somehow scan touchOSC's layout file and automatically generate
OSC message handlers for event dispatch.

For questions regarding this module contact Anonymous Researcher 
 <uumrz@clrmail.com>.
"""
import optparse
import threading
import Queue
import time
import sys
import traceback
import re
import json
import OSC

try:
    import zmq
except ImportError:
    try:
        import libpyzmq as zmq
    except ImportError:
        print 'no zmq installed'
        pass

from TangibleEvents import Event, EventListener
import TangibleEvents
from controller import DeviceController, ContinuousControl

##These constants are such a hack. I need to fish out my tangible code
#ROTATE, BUTTON, SLIDE = 0, 1, 2
#TOUCH_OSC_DEV_EVENT_DICT = {'rotary':ROTATE, 'toggle':BUTTON, 'fader':SLIDE, 'push':BUTTON}

#a Regular Expression Pattern for detecting UI elements within touchOSC
addr_regexpr = re.compile(r'(((multitoggle\d+/\d+)|(multifader\d+))/\d+)|(rotary|fader|push|toggle|xy)\d+')

eventQueue = Queue.Queue()

class InteractionMessageBusEndpoint( threading.Thread ):
    def __init__(self, host='127.0.0.1', port=10000, isStandalone=False):
        global eventQueue
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.device_proxy_mappings  = {} #A map from devices to proxies
        if isStandalone:
            self.inputQueue = eventQueue
        else:
            self.inputQueue = Queue.Queue()
    
    def _setInputQueue(self, inQ):
        self.inputQueue = inQ
        
    def addEvent(self, event):
        #TODO add mutual exclusion logic
        self.inputQueue.put(event)
    
    def quit(self):
        self.running = False
        
    def run ( self ):
      global eventQueue
      global device_proxy_map
      self.running = True
      s = self.sock
      ctx = zmq.Context() #TODO: check out these params
      #TODO: just built against latest build of pyzmq, broke some stuff
      s = zmq.Socket(ctx, zmq.PUB)
      if not self.host.startswith('tcp://'):
        self.host = 'tcp://'+self.host
      self.host = self.host+":"+str(self.port)
      print self.host
      '''
      Normally a server would create a socket and bind it to an
      address, but this creates a tight coupling dependency between
      the server and any connecting clients.
      I plan to use th
      e zmq_forwarder to decouple servers & clients,
      enabling them to come online/offline without nasty crashes/hangups
      '''
      s.connect(self.host)
      
      while not eventQueue.empty():
        print eventQueue.qsize()
        eventQueue.get()
        
      while self.running:
        time.sleep(0.05)
        data = self.inputQueue.get()
        print 'data ', data, type(data)
        #print 'got some data! ', data
        if data:
            topic = ''
            try:
                if data.__class__ is TangibleEvents.Event:
                    topic = data.handle+'\x00'
                msg = topic+data.toJSONFormattedMessage()
                print msg
                s.send(msg)
            except:
                traceback.print_exc()
                while not self.inputQueue.empty():
                  print self.inputQueue.qsize()
                  self.inputQueue.get()
                pass
        data = None

def defaultPrintHandler(addr, tags, data, source):
    print '-------'
    print addr
    print tags
    print data
    print source
    print '-------'

class touchOSCHandlers:
    """Class for objects dispatching events to touchOSC widgets proxies.
    """
    def __init__(self, endpoint=None, throttle=0.0165):
        self.interactors = []
        self.messageBusEndpoint = endpoint #an instance of InteractionMessageBusEndpoint
        self.eventDelayThreshold = throttle #controls num of events/sec
        self.prevEventTimestamp = 0
            
    def rotate(self, handle):
        print 'ROTATE'
    def slide(self, handle):
        print 'SLIDE'
    def push(self, handle):
        print 'PUSH'
    def switch(self, handle):
        print 'SWITCH'
    def point(self, handle):
        print 'POINT'
    
    def dispatchEvent(self, eventType, interactorHandle, val):
        if self.messageBusEndpoint is None:
            pass
        #TODO deal with value types, currently list values ...
        currentEventTimestamp = time.time() #need to throttle events
        elapsed = currentEventTimestamp - self.prevEventTimestamp
        if elapsed > self.eventDelayThreshold:
            event = TangibleEvents.Event(handle=interactorHandle, \
                                     type=eventType, value=val)
            self.messageBusEndpoint.addEvent(event)
        self.prevEventTimestamp = currentEventTimestamp
            
    def handleOSCMessage(self, addr, tags, value, source):
        """Scan OSC message address and trigger appropriate interaction  
           device event.
           This method will be passed as a callback argument to
           OSCServer.addMsgHandler(). The addMsgHandler() method doesn't use 
           keyword arguments, so order in you declare formal parameters matters.
        """ 
        m  = addr_regexpr.search(addr)
        if m:
            interactor = m.group()
            if m.group not in self.interactors:
                self.interactors.append(interactor)
            if re.search(r'rotary', interactor):
                self.dispatchEvent(TangibleEvents.ROTATE, interactor, value[0])
            elif re.search(r'fader', interactor):
                self.dispatchEvent(TangibleEvents.SLIDE, interactor, value[0])
            elif re.search(r'toggle', interactor):
                self.dispatchEvent(TangibleEvents.SWITCH, interactor, value[0])
            elif re.search(r'push', interactor):
                if value == 0:
                    self.dispatchEvent(TangibleEvents.BUTTONUP, interactor, value[0])
                else:
                    self.dispatchEvent(TangibleEvents.BUTTONDOWN, interactor, value[0])
            elif re.search(r'xy', interactor):
                self.point(interactor)
                self.dispatchEvent(TangibleEvents.POINT, interactor, value)
        else:
            print addr, value


class TouchOSCInteractorProxy(touchOSCHandlers, DeviceController):
    """docstring for TouchOSCInteractorProxy"""
    def __init__(self):
        #super(TouchOSCInteractorProxy, self).__init__()
        touchOSCHandlers.__init__(self)
        DeviceController.__init__(self)
    
    #override  touchOSCHandlers.dispatchEvent
    def dispatchEvent(self, event_type, interactor_handle, val):
        currentEventTimestamp = time.time() #need to throttle events
        elapsed = currentEventTimestamp - self.prevEventTimestamp
        if elapsed > self.eventDelayThreshold:
            event = TangibleEvents.Event(handle=interactor_handle, \
                                     type=event_type, value=val)
            try:
                ix = self._devices_map[event.handle]
                event.source = ix
                ix.onSelection(event)
            except KeyError:
                #device proxy hasn't been added
                pass
        self.prevEventTimestamp = currentEventTimestamp
    
    #override DeviceController.addDevice
    def addDevice(self, handle):
        device = ContinuousControl(0.0, 1.0)
        self._devices_map[handle] = device


def main(argv):
    parser = optparse.OptionParser("usage: %prog -H arg1 -P arg2")
    parser.add_option('-H', dest='hostname', default='127.0.0.1', type='string')
    parser.add_option('-P', dest='portnum', default=9000, type='int')
    #TODO add options for setting host, port for touchOSC device
    options, args = parser.parse_args()
    hostname = options.hostname
    portnum = options.portnum    
    oscServer = OSC.OSCServer((hostname, portnum))
    
    interactionMessageBusServer = InteractionMessageBusEndpoint()
    interactionMessageBusServer.start()
    
    handler = touchOSCHandlers(endpoint=interactionMessageBusServer)
    oscServer.addMsgHandler('default', defaultPrintHandler)
    oscServer.addMsgHandler('default', handler.handleOSCMessage)
    
    serverThrd = threading.Thread(target=oscServer.serve_forever)
    serverThrd.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        interactionMessageBusServer.quit()
        sys.exit(0)
        #oscServer.close()
        #serverThrd.join()
    
if __name__ == '__main__':
    main(sys.argv)
    
