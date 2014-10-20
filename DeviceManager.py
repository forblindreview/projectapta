# -*- coding: utf-8 -*-
import threading,serial, thread
import sys, time,pyinotify
import socket
import os, os.path
from daemon import Daemon
from pyinotify import WatchManager, Notifier, ProcessEvent, EventsCodes, IN_CREATE, IN_DELETE
import select
import os
import fcntl
import struct , Queue
import exceptions
import commands
import cPickle
import json
import uuid
try:
    import zmq
except ImportError:
    import libpyzmq as zmq
import servicesMessages
import messageTypes
import traceback
import TangibleEvents


portNum =  10101
input_event_struct = "@llHHi"
input_event_size = struct.calcsize(input_event_struct)

EVENT_BUTTON_PRESS = 1
EVENT_RELATIVE_MOTION = 2
RELATIVE_AXES_DIAL = 7
BUTTON_MISC = 0x100

wm = WatchManager()
try:
    maskCreate = EventsCodes.IN_CREATE  # watched events
    maskDelete = EventsCodes.IN_DELETE 
    maskAll = EventsCodes.IN_DELETE | EventsCodes.IN_CREATE
except:
    from pyinotify import IN_CREATE, IN_DELETE
    maskCreate = IN_CREATE  # watched events
    maskDelete = IN_DELETE 
    maskAll = IN_DELETE | IN_CREATE
   

###################################################################################################
#Powermate class 
powerMateDev = Queue.Queue ()
eventQueue = Queue.Queue(50)
rfidDev = Queue.Queue()
watchQueue = Queue.Queue()
bladedDev = Queue.Queue()

'''
using the expression below to generate a map for reverse lookups
dict((v,k) for k, v in map.iteritems())
'''
def invert_dict(d):
    return dict([(v,k) for k,v in d.iteritems()])

connected_devices_lst = []
proxy_devices_map = {}
device_proxy_map = {}



class DeviceTypes:
    DEVICE_ID20_RFID = 20
    DEVICE_BLADES_TILES = 21


class PowerMate( threading.Thread ):
    def __del__(self):
        if self.handle >= 0:
            self.poll.unregister(self.handle)
            os.close(self.handle)
            self.handle = -1
            del self.poll
    def OpenDevice(self, filename):
        try:
            self.handle = os.open(filename, os.O_RDWR)
            if self.handle < 0:
                return 0
            name = fcntl.ioctl(self.handle, 0x80ff4506, chr(0) * 256) # read device name
            name = name.replace(chr(0), '')
            if name == 'Griffin PowerMate' or name == 'Griffin SoundKnob':
                fcntl.fcntl(self.handle, fcntl.F_SETFL, os.O_NDELAY)
                return 1
            os.close(self.handle)
            self.handle = -1
            return 0
        except exceptions.OSError:
            return 0
    def run ( self ):
      global powerMateDev
      global eventQueue
      global connected_devices_lst
      device = powerMateDev.get()
      time.sleep(0.1)  # see if you can get rid of this 
      if device != None:
	self.handle = -1
	self.status = self.OpenDevice(device)
	if self.status == 1:
	    self.poll = select.poll()
	    self.poll.register(self.handle, select.POLLIN)
	    pressEvent = 'U'
	    rotEvent = 'C'
	    #eventQueue.put_nowait('powermate' + device[device.find('event')+5:] +','+'entry')
            #connected_devices_lst.append(device)
            dev_identifier = 'powermate' + device[device.find('event')+5:]
            connected_devices_lst.append(dev_identifier)
	    while(os.path.exists(device)):
		time.sleep(0.05)
		try:
		    data = os.read(self.handle, input_event_size * 32)
                    event = TangibleEvents.Event(handle=dev_identifier)
		    if data != '':
                        powData = struct.unpack(input_event_struct, data[0:input_event_size])
			if powData[3] == 256:
			    if powData[4] == 1:
				pressEvent = 'D'
				rotEvent = 'C'
                                event.type = TangibleEvents.BUTTONDOWN
			    else:
				pressEvent = 'U'  
				rotEvent = 'C'
                                event.type = TangibleEvents.BUTTONUP
			else:
			    if powData[4] > 0:
				rotEvent = 'R'
			    else :
				rotEvent = 'L'
                            rotEvent+=str(powData[4])
                            event.type = TangibleEvents.ROTATE
                            event.value = powData[4]
			#eventQueue.put([dev_identifier ,  ', '+pressEvent, ', '+rotEvent])
			data = data[input_event_size:]
                        eventQueue.put(event)
		except exceptions.OSError, e:
		    pass
	    #eventQueue.put_nowait('powermate' + device[device.find('event')+5:]+','+'exit')
            connected_devices_lst.remove(device)
	    thread.exit()	
####################################################################################

class rfidOlm( threading.Thread ):
    def run ( self ):
      global rfidDev
      global eventQueue
      device = rfidDev.get()
      time.sleep(0.1)  # see if you can get rid of this 
      if device != None:
	    ser = serial.Serial(device, timeout=1)
	    ser.flushInput() 
	    #eventQueue.put_nowait('rfid' + device[device.find('ttyACM')+6:]+','+'entry')
            dev_handle = '%s.OLIMEXRFID' % (device)
	    while(os.path.exists(device)):
		    time.sleep(0.1)
		    try:
			    rfid = ser.read(16)
		    except:	
			    ser.close() 
                            thread.exit()
		    if rfid :
                        start = rfid.find('-') + 1
                        rfid = rfid[start:start+10]
                        event = TangibleEvents.Event(handle=dev_handle, type=TangibleEvents.TAGENTRY, value=rfid)
                        eventQueue.put(event)

class bladedDeviceSlurper( threading.Thread ):
    def run ( self ):
      global bladedDev
      global eventQueue
      device = bladedDev.get()
      time.sleep(0.1)  # see if you can get rid of this 
      if device != None:
        connected_devices_lst.append(device)
        ser = serial.Serial(device, baudrate=9600, timeout=0.1)
        ser.flushInput() 
        #eventQueue.put_nowait('blades+tiles' + device[device.find('ttyUSB')+6:]+','+'entry')
        port = device.strip("/dev/")
        firstRead = True
        device_type = 0
        while(os.path.exists(device)):
            time.sleep(0.05)
            try:
                event_str = ser.readline()
                if event_str is not '':
                    #print 'Device %s: event %s ' % (device, event_str)
                    if firstRead:
                        if event_str[0] == '\x02':
                            print 'RFID'
                            device_type = DeviceTypes.DEVICE_ID20_RFID
                        else:
                            print 'Blades+Tiles'
                            ser.setBaudrate(57600)
                            device_type = DeviceTypes.DEVICE_BLADES_TILES
                        firstRead = False
                    msg = None
                    if device_type is DeviceTypes.DEVICE_BLADES_TILES:
                        #if event_str:
                        fields = event_str.strip(' /\n').split(' ')
                        #print fields
                        try:
                            if 'EVT' in fields:
                                fields.insert(0, device)
                                dev_handle = device+'.'+fields[2]
                                event = TangibleEvents.Event(handle=dev_handle, type=TangibleEvents.ROTATE, value=int(fields[4], 16))
                                eventQueue.put(event)
                                #msg = json.write(fields)
                            if 'DEV' in fields:
                                pass
                        except ValueError:
                            traceback.print_exc()
                    elif device_type is DeviceTypes.DEVICE_ID20_RFID:
                        dev_handle = '%s.ID20RFID'%(device)
                        event = TangibleEvents.Event(handle=dev_handle, type=TangibleEvents.TAGENTRY, value=event_str[1:13])
                        eventQueue.put(event)
                    else:
                        pass
                    del event_str
                        
            except:
                traceback.print_exc()
                traceback.print_stack()
                ser.close() 
                thread.exit()
            
        connected_devices_lst.remove(device)
        print '!!!!!!!!! I\'m bailing, the device is gone!!'


###################################################################################################
class dataServ( threading.Thread ):
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
      #s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      #s.bind ( ( '', portNum ) )
      #s.listen(5)
      #conn, addr = s.accept()
      self.running = True
      s = self.sock
      ctx = zmq.Context(1,1,0) #TODO: check out these params
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
                ##print 'data ', data
                #msg = data
                #topic = ''
                #if data[0].find('powermate') is not -1:
                #    dev_handle = '/dev/input/event'+data[0].strip('powermate')
                #    
                #    try:
                #        #topic = device_proxy_map[dev_handle]+'@\x00'
                #        topic = dev_handle+'\x00'
                #        #topic = 'foo\x00'
                #    except KeyError:
                #        pass
                #else:
                #    topic = ''
                #    try:
                #        #topic = device_proxy_map[data[0]]+'@\x00'
                #        topic = data[0]+'@\x00'
                #    except KeyError:
                #        pass
                msg = topic+data.toJSONFormattedMessage()
                print msg
                s.send(msg)
            except:
                traceback.print_exc()
                #conn.close()
                #conn, addr = s.accept()
                while not self.inputQueue.empty():
                  print self.inputQueue.qsize()
                  self.inputQueue.get()
                pass
        data = None
        #req = s.recv(1)
        #if req is not None:
            #process request



class requestHandler(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = False
        self.sock = None
        
    def quit(self):
        self.running = False
        time.sleep(0.5)
        try:
            self.sock.close()
        except exception:
            print exception
            pass
        
    def run(self):
        global connected_devices_lst
        global proxy_devices_map
        global device_proxy_map
        self.running = True
        try:
            ctx = zmq.Context()
            s = self.sock
    
            s = zmq.Socket(ctx, zmq.REP)
            s.bind('tcp://127.0.0.1:10777')
        except:
            print 'didn\'t get a connection, bailing out now...'
            return
        
        while self.running:
            req = s.recv()
            print "Got request: "+req
            rep = ''
            req_data = json.read(req)
            if req_data[0] is not messageTypes.REQ:
                rep = servicesMessages.errorMessage("ERROR: undefined message")
            else:
                req_type = req_data[1]
                if  req_type is messageTypes.REQUEST_PROXY:
                    #create a proxy_id
                    proxy_uuid = uuid.uuid1()
                    #add it to active proxy list
                    proxy_devices_map[proxy_uuid] = []
                    #reply to requester
                    rep = servicesMessages.replyProxyMessage(proxy_uuid.__str__())
                    pass
                elif req_type is messageTypes.REQUEST_ADD_DEVICE_TO_PROXY:
                    #get proxy id
                    prxy_id = uuid.UUID(req_data[2])
                    handle = req_data[3]
                    proxy_devices_map[prxy_id].append(handle)
                    device_proxy_map[handle] = prxy_id.fields[0].__hex__()
                    rep = servicesMessages.replyDeviceAddedToProxy(req_data[2], handle)
                    print "ADDITON REQUEST ", rep
                    
                    #get dev handle
                    #add handle to dev proxy dict if available
                    #reply to requester
                    pass
                elif req_type is messageTypes.REQUEST_REMOVE_DEVICE_FROM_PROXY:
                    pass
                elif req_type is messageTypes.REQUEST_AVAILABLE_DEVICES_LIST:
                    rep = servicesMessages.replyAvailableDevicesList(connected_devices_lst)
                else:
                    rep  = servicesMessage.errorMessage("ERROR: unsupported request")
            s.send(rep)
            print 'sent reply: ', rep
            time.sleep(0.1)

###################################################################################################
#Inotify reg and add the event to a queue
class PTmpCreate (ProcessEvent):
	def process_IN_CREATE(self, event):
		global powerMateDev
		global rfidDev
                global bladedDev
		#eventQueue.put(event.name)
                #print 'Device Creation Event'
                #print 'Device port ', event.__dict__
		if   (event.name[0:5] == "event")  and (event.path == "/dev/input") :
			this = event.path + "/" + event.name
			powerMateDev.put (this)
			PowerMate().start()
			pass
			
		elif  (event.name[0:6] == "ttyACM")  and (event.path == "/dev") :
			this = event.path + "/" + event.name
			rfidDev.put (this)
			rfidOlm().start()
			pass
                elif  (event.name[0:6] == "ttyUSB")  and (event.path == "/dev") :
			this = event.path + "/" + event.name
			bladedDev.put (this)
			bladedDeviceSlurper().start()
			pass
			
class newDev(threading.Thread):
	def run (self):
		global  watchQueue
		toWatch = watchQueue.get()
		if toWatch :
			notifier = Notifier(wm, PTmpCreate())
			wdd = wm.add_watch(toWatch, maskCreate, rec=True)
			while True:  # loop forever
				time.sleep(1)
				try:
					notifier.process_events()
					if notifier.check_events():
						notifier.read_events()
				except KeyboardInterrupt:
					notifier.stop()
					break
			
###################################################################################################
class MyDaemon(Daemon):
	def run (self):
	      global eventQueue
              for i in range(30):
                if (os.path.exists('/dev/input/event%s'%i)):
                  powerMateDev.put('/dev/input/event%s'%i)
		  PowerMate().start()
		if (os.path.exists('/dev/ttyACM%s'%i)):
                  rfidDev.put('/dev/ttyACM%s'%i)  
		  rfidOlm().start()
	      dataServ().start()
	      watchQueue.put('/dev/input')
	      newDev().start()
	      watchQueue.put('/dev')
	      newDev().start()
              while True:
                      time.sleep(0.1)

if __name__ == "__main__":
   global eventQ
   for i in range(30):
      if (os.path.exists('/dev/input/event%s'%i)):
         powerMateDev.put('/dev/input/event%s'%i)
         PowerMate().start()
      if (os.path.exists('/dev/ttyACM%s'%i)):
         rfidDev.put('/dev/ttyACM%s'%i)
         rfidOlm().start()
      if (os.path.exists('/dev/ttyUSB%s'%i)):
         bladedDev.put('/dev/ttyUSB%s'%i)
         bladedDeviceSlurper().start()
   req_handler = requestHandler()
   req_handler.start()
   dataServ(host='tcp://127.0.0.1', port='10000', isStandlone=True).start()
   watchQueue.put('/dev/input')
   newDev().start()
   watchQueue.put('/dev')
   newDev().start()
   #alive().start()
   while True:
     try:
        time.sleep(0.01)
     except KeyboardInterrupt:
        sys.exit()
