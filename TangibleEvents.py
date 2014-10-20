#!/usr/bin/env python
import json
from PropertyUtils import prop

ROTATE, BUTTONDOWN, BUTTONUP, TAGENTRY, \
 TAGEXIT, SLIDE, SWITCH, POINT = range(8)

class Event(object):
    def __init__(self, handle = '', source=None, type=-99, value=-99):
        self.handle = handle
        self.source = source
        self.type = type
        self.value = value
        self._id = None
        self._time_stamp = None
        self._skew = None
	#TODO: change 'value' to 'state' b/c value is a C# reserved word 
    
    def toJSONFormattedMessage(self):
        try:
            return json.write(self.__dict__)
        except json.WriteException:
            return ""
        
    def fromJSONFormattedMessage(self, json_msg):
        msg_dict = json.read(json_msg)
        self.handle  = msg_dict['handle']
        self.source = msg_dict['source']
        self.type = msg_dict['type']
        self.value = msg_dict['value']
        self._skew = msg_dict['_skew']
        self._time_stamp = msg_dict['_time_stamp']
        self._id = msg_dict['_id']
        return self
    
    @prop
    def id(): pass
    
    @prop
    def time_stamp(): pass

    @prop
    def skew(): pass

class EventListener(object):
    def handleEvent(self, event):
        ''' Unimplemented method to handle events on event's source '''
        pass
