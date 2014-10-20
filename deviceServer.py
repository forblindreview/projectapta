# -*- coding: utf-8 -*-
import threading,serial
import sys, time,pyinotify
import socket
import os, os.path
from daemon import Daemon
from pyinotify import WatchManager, Notifier, ProcessEvent, EventsCodes
import select
import os
import fcntl
import struct , Queue
import exceptions
import commands
import cPickle
import json

portNum =  10101
input_event_struct = "@llHHi"
input_event_size = struct.calcsize(input_event_struct)

EVENT_BUTTON_PRESS = 1
EVENT_RELATIVE_MOTION = 2
RELATIVE_AXES_DIAL = 7
BUTTON_MISC = 0x100

wm = WatchManager()
maskCreate = EventsCodes.IN_CREATE  # watched events
maskDelete = EventsCodes.IN_DELETE 
maskAll = EventsCodes.IN_DELETE | EventsCodes.IN_CREATE


###################################################################################################
#Powermate class 
powerMateDev = Queue.Queue ()
eventQueue = Queue.Queue(50)
rfidDev = Queue.Queue()
watchQueue = Queue.Queue()
bladedDev = Queue.Queue()

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
	    eventQueue.put_nowait('powermate' + device[device.find('event')+5:] +','+'entry')
	    while(os.path.exists(device)):
		time.sleep(0.05)
		try:
		    data = os.read(self.handle, input_event_size * 32)
		    if data != '':
                        powData = struct.unpack(input_event_struct, data[0:input_event_size])
			if powData[3] == 256:
			    if powData[4] == 1:
				pressEvent = 'D'
				rotEvent = 'C'
			    else:
				pressEvent = 'U'  
				rotEvent = 'C'
			else:
			    if powData[4] > 0:
				rotEvent = 'R'
			    else :
				rotEvent = 'L'       
			eventQueue.put('powermate' + device[device.find('event')+5:] + ', '+pressEvent+', '+rotEvent)
			data = data[input_event_size:]
		except exceptions.OSError, e:
		    pass
	    eventQueue.put_nowait('powermate' + device[device.find('event')+5:]+','+'exit')	
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
	    eventQueue.put_nowait('rfid' + device[device.find('ttyACM')+6:]+','+'entry')
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
				    eventQueue.put_nowait('rfid'+ device[device.find('ttyACM')+6:]+','+rfid)

class bladedDeviceSlurper( threading.Thread ):
    def run ( self ):
      global bladedDev
      global eventQueue
      device = bladedDev.get()
      time.sleep(0.1)  # see if you can get rid of this 
      if device != None:
	    ser = serial.Serial(device, baudrate=57600, timeout=0.1)
	    ser.flushInput() 
	    eventQueue.put_nowait('blades+tiles' + device[device.find('ttyUSB')+6:]+','+'entry')
            port = device.strip("/dev/")
	    while(os.path.exists(device)):
		    time.sleep(0.1)
		    try:
			    event = ser.readline()
		    except:	
			    ser.close() 
                            thread.exit()
		    if event:
                            msg = "b+t_tray@"+port+' ' , event
                            eventQueue.put(msg)


###################################################################################################
class dataServ( threading.Thread ):
    def run ( self ):
      global eventQueue
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.bind ( ( '', portNum ) )
      s.listen(5)
      conn, addr = s.accept()
      while not eventQueue.empty():
        print eventQueue.qsize()
        eventQueue.get()
      print conn
      while (1):
	time.sleep(0.05)
	data = eventQueue.get()
	if data:
	  try:
	    conn.send(json.write(data))
	  except:
	      conn.close()
	      conn, addr = s.accept()
              while not eventQueue.empty():
                print eventQueue.qsize()
                eventQueue.get()
              
	      #while data:
		#data = eventQueue.get()

###################################################################################################
#Inotify reg and add the event to a queue
class PTmpCreate (ProcessEvent):
	def process_IN_CREATE(self, event):
		global powerMateDev
		global rfidDev
                global bladedDev
		#eventQueue.put(event.name)
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
   dataServ().start()
   watchQueue.put('/dev/input')
   newDev().start()
   watchQueue.put('/dev')
   newDev().start()
   #alive().start()
   while True:
     try:
        time.sleep(0.001)
     except KeyboardInterrupt:
        sys.exit()
