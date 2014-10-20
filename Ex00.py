#!/usr/bin/env python
import controller
import time
import zmq

import TangibleEvents

from DeviceProxy import *

card_ids = ['1C0049081548', '1D00321E7948', '1D0031F617CD', 
'1D003230948B', '1C004919723E']
card_bindings = ['view','speak','sunRise','volcanoErupt','oilSpill']
card_types =['action', 'action', 'data', 'data', 'data']
reader_types = ['action', 'data']
ACTION_READER_HANDLER = '/dev/ttyUSB3.ID20RFID'
DATA_READER_HANDLER = '/dev/ttyUSB2.ID20RFID'

database = {}
for (id, binding, type) in zip(card_ids, card_bindings, card_types):
    database[id] = (type, binding)

current_action_id = ''
current_data_id   = ''
dependencies = {}
dependencies['action'] = current_data_id
dependencies['data'] = current_action_id

class RotateEventListener(TangibleEvents.EventListener):
    def handleEvent(self, event):
        print 'source: ', event.source, ' value: ', event.value


class EntranceEventListener(TangibleEvents.EventListener):
    def __init__(self, type):
        global current_data_id, current_action_id, dependencies
        self.type = type
        self.reader_dependency = dependencies[type]
    def handleEvent(self, event):    
        global current_data_id, current_action_id
        #check id type
        tag_id = event.value
        event_type = ''
        binding = ''
        try:
            (event_type, binding) = database[tag_id]
        except KeyError:
             print 'Error: Unrecognized tag id!!'
             return
        if event_type is not self.type:
             print 'Error: Non-%s card place on %s reader!'% (self.type, self.type)
             return
        #Handle event
        print ' Tag <%s> (type <%s>) enters <%s> reader' % (tag_id, event_type, self.type)
        if self.type is 'data':
            current_data_id = tag_id
	    print 'Set data card id to %s' %(current_data_id)
        elif self.type is 'action':
            current_action_id = tag_id
	    print 'Set action card id to %s' %(current_action_id)
        
	#check if both noun and verb are present
	(dependent_type, dependent_tag) = ('data', current_action_id) if self.type == 'action' else ('action', current_action_id)
        if dependent_tag is '':
	    print '%s specified , now use a %s card!' %(self.type.upper(), dependent_type)
            return
        which_action = ''
        which_data = ''
        try:
            if self.type is 'action':
                which_action = binding
                (type, which_data) = database[current_data_id]
            elif self.type is 'data':
                which_data = binding
                (type, which_action) = database[current_action_id]
        #perform action
        except KeyError:
            pass
        print 'Executing action <%s> on data <%s>!' %(which_action, which_data)



def main():
    control = controller.DeviceController()
    control.addDevice(ACTION_READER_HANDLER)
    control.addDevice(DATA_READER_HANDLER)

    action_reader = control.getDevice(ACTION_READER_HANDLER)
    data_reader = control.getDevice(DATA_READER_HANDLER)
   
    action_listener = EntranceEventListener('action')
    data_listener =  EntranceEventListener('data')

    action_reader.addListener(TangibleEvents.TAGENTRY, action_listener)
    data_reader.addListener(TangibleEvents.TAGENTRY, data_listener)

    
    control.start()
    time.sleep(2)
    
    event1 = TangibleEvents.Event(handle=ACTION_READER_HANDLER, source=action_reader, type=TangibleEvents.TAGENTRY, value='1D003230948B')
    event2 = TangibleEvents.Event(handle=DATA_READER_HANDLER, source=data_reader, type=TangibleEvents.TAGENTRY, value='1D003230948B')
    event3 = TangibleEvents.Event(handle=ACTION_READER_HANDLER, source=action_reader, type=TangibleEvents.TAGENTRY, value='1C0049081548')
    
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
