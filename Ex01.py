#!/usr/bin/env python
import controller
import time
import zmq
import sqlite3
import TangibleEvents
from DeviceProxy import *

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

class EntranceEventListener(TangibleEvents.EventListener):
    def __init__(self, type):
        global dependencies
        self.type = type
        self.reader_dependency = dependencies[type]
    
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
            current_data_id = tag_id
            print 'Set data card id to %s' %(current_data_id)
        elif self.type == 'action':
            current_action_id = tag_id
            print 'Set action card id to %s' %(current_action_id)
        
        #check if both noun and verb are present
        (dependent_type, dependent_tag) = ('data', current_action_id) if self.type == 'action' else ('action', current_action_id)
        if dependent_tag == '':
            print '%s specified , now use a %s card!' %(self.type.upper(), dependent_type)
            return
        which_action = ''
        which_data = ''
        if self.type == 'action':
            which_action = binding
            db_cursor.execute('SELECT binding FROM cards WHERE ID="%s"'%(current_data_id))
            query_result = db_cursor.fetchone()
            if query_result is None:
                print 'Error: tag id %s not found'%(current_data_id)
                return
            (which_data) = query_result
        elif self.type == 'data':
            which_data = binding
            db_cursor.execute('SELECT binding FROM cards WHERE ID="%s"'%(current_action_id))
            query_result = db_cursor.fetchone()
            if query_result is None:
                print 'Error: tag id %s not found'%(current_action_id)
                return
            (which_action) = query_result
        #perform action
        print 'Executing action <%s> on data <%s>!' %(which_action, which_data)



def main():
    #Initialize device controller
    control = controller.DeviceController()
    control.addDevice(ACTION_READER_HANDLE)
    control.addDevice(DATA_READER_HANDLE)
    #Get proxies for devices
    action_reader = control.getDevice(ACTION_READER_HANDLE)
    data_reader = control.getDevice(DATA_READER_HANDLE)
    #Define event listeners on reader devices
    action_listener = EntranceEventListener('action')
    data_listener =  EntranceEventListener('data')
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
    data_reader._onSelection(event2)
    time.sleep(2)
    action_reader._onSelection(event3)
    
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
