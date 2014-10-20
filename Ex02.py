#!/usr/bin/env python
import controller
import time
import zmq
import sqlite3
import TangibleEvents
from DeviceProxy import *

from Observable import Observable, Observer

#Global variables
ACTION_READER_HANDLE = '/dev/ttyUSB1.ID20RFID'
DATA_READER_HANDLE = '/dev/ttyUSB0.ID20RFID'
current_action_id = ''
current_data_id   = ''
dependencies = {}
dependencies['action'] = current_data_id
dependencies['data'] = current_action_id
db_conn =  sqlite3.connect('datacards.db')
db_cursor = db_conn.cursor()

DEBUG_LEVEL = 0
from debugUtils import printdebug

class ActionDataBinding(Observable):
    def __init__(self, action = None, data=None):
        Observable.__init__(self)
        self._action = action
        self._data = data
    
    def setAction(self, action):
        #TODO Add synchronization
        #print 'DEBUG: entering ActionDataBinding.setAction()'
        self._action = action
        self.notify()
        #print 'DEBUG: exiting ActionDataBinding.setAction)'

    def setData(self, data):
        #TODO Add synchronization
        #print 'DEBUG: entering ActionDataBinding.setData()'
        self._data = data
        self.notify()
        #print 'DEBUG: exiting ActionDataBinding.setData()'


class ActionDataBindingObserver(Observer):
    def __init__(self, action_data_binding = None):
       self._binding = action_data_binding
       self._binding.addObserver(self)

    def update(self, **kwargs):
        #print 'DEBUG: entering ActionDataBindingObserver.update()'
        (action, data) = (self._binding._action, self._binding._data)
        #print '    DEBUG: action: ', action
        #print '    DEBUG: data: ', data
        if data <> None and action <> None:
            print 'Executing action <%s> on data <%s>!'%(action, data)
        elif data is None:
            if action is not None:
                print 'Action specified, now use a data card!'
        else:
            if data is not None:
                print 'Data specified, now use a action card!'
        #print 'DEBUG: exiting ActionDataBindingObserver.update()'


class EntranceEventListener(TangibleEvents.EventListener):
    def __init__(self, type, action_data_binding=None):
        global dependencies
        self.type = type
        self.reader_dependency = dependencies[type]
        self.td_binding = action_data_binding
    
    def handleEvent(self, event):    
        global current_data_id, current_action_id, db_conn, db_cursor
        #Get Tag ID
        tag_id = event.value
        event_type = ''
        binding = ''
        #Query Database
        db_cursor.execute('SELECT type,binding FROM cards WHERE ID="%s"'%(tag_id))
        query_result = db_cursor.fetchone()
        if query_result is None:
            print 'Error: Unrecognized tag id!!'
            return
        (event_type, binding) = query_result
        #Check type of card against bound type for RFID Reader
        if event_type <> self.type:
             print 'Error: Non-%s card place on %s reader!'% (self.type, self.type)
             return
        #Handle event
        print ' Tag <%s> (type <%s>) enters <%s> reader' % (tag_id, event_type, self.type)
        if self.type == 'data':
            if self.td_binding is not None: 
                self.td_binding.setData(binding)
            current_data_id = tag_id
            print 'Set data card id to %s' %(current_data_id)
        elif self.type == 'action':
            if self.td_binding is not None: 
                self.td_binding.setAction(binding)
            current_action_id = tag_id
            print 'Set action card id to %s' %(current_action_id)
            


def main():
    action_data_binding = ActionDataBinding()
    action_data_controller = ActionDataBindingObserver(action_data_binding)
    #Initialize device controller
    control = controller.DeviceController()
    control.addDevice(ACTION_READER_HANDLE)
    control.addDevice(DATA_READER_HANDLE)
    #Get proxies for devices
    action_reader = control.getDevice(ACTION_READER_HANDLE)
    data_reader = control.getDevice(DATA_READER_HANDLE)
    #Define event listeners on reader devices
    action_listener = EntranceEventListener('action', action_data_binding)
    data_listener =  EntranceEventListener('data', action_data_binding)
    action_reader.addListener(TangibleEvents.TAGENTRY, action_listener)
    data_reader.addListener(TangibleEvents.TAGENTRY, data_listener)
    #Start the event handling loop for device controller
    control.start()
    time.sleep(2)
    #Generate RFID tag entrance events
    event1 = TangibleEvents.Event(handle=ACTION_READER_HANDLE, source=action_reader, type=TangibleEvents.TAGENTRY, value='1D003230948B')
    event2 = TangibleEvents.Event(handle=DATA_READER_HANDLE, source=data_reader, type=TangibleEvents.TAGENTRY, value='1D003230948B')
    event3 = TangibleEvents.Event(handle=ACTION_READER_HANDLE, source=action_reader, type=TangibleEvents.TAGENTRY, value='1C0049081548')
    #Manually invoke events
    action_reader._onSelection(event1)
    time.sleep(2)
    action_reader._onSelection(event3)
    time.sleep(2)
    data_reader._onSelection(event2)
    
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
