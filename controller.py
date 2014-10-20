#!/usr/bin/env python

import re

import zmq #bau -- seeing if I can remove...
import time, threading
import TangibleEvents

class DeviceController(threading.Thread):
  def __init__(self, remote=True, host='127.0.0.1', port='10778'):
     threading.Thread.__init__(self)
     self.devices = []
     self.verbose = False
     self._topics = []
     self._devices_map = {}
     self._host = host
     self._port = port
     if remote is True:
        self.initializeRemote()
     self._running = False
     print 'controller initialized'
     #self._sock = None
     #self._ctx = None
    
  def initializeRemote(self):
     self._ctx = zmq.Context(2)
     self._sock = zmq.Socket(self._ctx, zmq.SUB)
     zmq_fmt_host = 'tcp://'+self._host+':'+self._port
     print zmq_fmt_host
     self._sock.setsockopt(zmq.SUBSCRIBE, '')
     self._sock.connect(zmq_fmt_host)
 
  def quit(self):
    self._running = False
     
  def addDevice(self, dev_handle):
     dev_topic = dev_handle+'\x00'
     print 'device topic ', dev_topic
     self._sock.setsockopt(zmq.SUBSCRIBE, dev_topic)
     self._topics.append(dev_topic)
     #instantiate device object
     if dev_handle.find('rotary') <> -1:
         interactor = Rotor(0.0, 1.0, 0.0)
     elif dev_handle.find('toggle') <> -1:
         interactor = DiscreteControl()
     else:
	 interactor = ContinuousControl()
     self._devices_map[dev_handle] = interactor
  
  def getDevice(self, handle):
    try:
      return self._devices_map[handle]
    except KeyError:
      return None

  def removeDevice(self, dev_handle):
     pass

  def extractEventMessage(self, msg):
     topic, message = msg.split('\x00')
     return message
  def run(self):
     self._running = True
     print 'starting subscription loop'
     while self._running:
#        msg = self._sock.recv(zmq.NOBLOCK, False)
        msg = self._sock.recv()
        if msg is not None:
          #print 'got message!!!'
          extracted_msg = self.extractEventMessage(msg)
          #print extracted_msg
          event = TangibleEvents.Event().fromJSONFormattedMessage(extracted_msg)
          try:
            control = self._devices_map[event.handle]
            event.source = control
            control.onSelection(event)
          except KeyError:
            # print 'KeyError!!!'
            pass
        #evt = TangibleEvents.Event().fromJSONFormattedMessage(msg)
        #1. get the message
        #2. extract the topic
        # message_fmt := <topic>\x00<json msg>
        #msg_sep = msg.split('\x00')
        #DEV EVENT POS *DELTA
        #POWERMATE ROTATE - 10
        #POWERMATE PUSHDOWN
        #POWERMATE PUSHUP
        #HAPTIC ROTATE 224
        #POTROT ROTATE 1
        #SHAFTENC ROTATE 16
        #dev = self._topics_devices_map[msg_sep[0]]
        # event_msg = json.read(msg_sep[1])
        #dev.onRotate(value)
        #3. invoke the event on appropiate device
        #4. 
        time.sleep(0.001)
     #self._sock.close()
  
class Control(object):
  def __init__(self):
     self._state = None
     self.listeners_map = {}
     
  
  def getSelection(self): abstract
     
  
  def setSelection(self, value): abstract
  
     
  def addListener(self, eventType, listener):
     try:
        self.listeners_map[eventType].append(listener)
     except KeyError:
        self.listeners_map[eventType] = [listener]
  
  def removeListener(self, listener):
     for eventType, listeners_lst in self.listeners_map.iteritems():
        for listener in listener_lst:
           if listener in listener_lst:
              listener_lst.remove(listener)
           
  def _onSelection(self, event):
     #if self.verbose:
     #   print 'Control::_onSelection'
     try:
        listeners_lst = self.listeners_map[event.type]
        for listener in listeners_lst:
           listener.handleEvent(event)
     except KeyError:
        pass
        
class DiscreteControl(Control):
  def __init__(self, states=[True, False]):
     self._states = states
     self._current_state = False
  
  def getSelection(self):
     return self._current_state
     
  def setSelection(self, selection):
     self._current_state = selection
     
class ContinuousControl(Control):
  def __init__(self, min = 0, max=0, init=0, isAbsolute=True):
     Control.__init__(self)
     self._min = min
     self._max = max
     self._state = init
     self.isAbsolute = isAbsolute
     
  def getSelection(self):
     return self._state
  def setSelection(self, selection):
     self._state = selection
   
  def getMin(self):
     return self._min
  
  def getMax(self):
     return self._max
  
  def setMin(self, value):
     self._min = value
  
  def setMax(self, value):
     self._max = value
     
  def onSelection(self, event):
    #print 'ContinuousControl::onSelection'
    Control._onSelection(self, event)
  
class Rotor(ContinuousControl):
   def __init__(self, min=0, max=0, init=0):
      ContinuousControl.__init__(self, min, max, init)
   
   def onRotate(self, value):
      event = Event(self, ROTATE, value)
      print 'Rotor::onRotate'
      ContinuousControl.onSelection(self, event)
#      
#class Button(DiscreteControl):
#   def __init__(self):
#      self._states = [DOWN, UP]
#   
#   def onPushDown(self):
#      self._current_state = self._states[0]
#      event = Event(self, PUSHDOWN, self._current_state)
#      self._onSelection(self, event)
#      
#   def onPushUp(self):
#      self._current_state = self._states[1]
#      event = Event(self, PUSHDOWN, self._current_state)
#      self._onSelection(self, event)
#      
