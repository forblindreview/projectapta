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

serverIP = 'localhost'
portNum = 10101
wm = WatchManager()
maskCreate = EventsCodes.IN_CREATE  # watched events
maskDelete = EventsCodes.IN_DELETE 
maskAll = EventsCodes.IN_DELETE | EventsCodes.IN_CREATE

class powermateEvent( threading.Thread ):
  def __init__(self):
    threading.Thread.__init__(self)
    self.running = False
  
  def quit(self):
    self.running = False
    time.sleep(0.5)
    self.sock.close()
    
  def run (self):
      self.running = True
      while(self.running):
          time.sleep(0.1)  
          print 'new dev'
          #device = newDevice.get()
          #if device != None:
          self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          try:
            self.sock.settimeout(1)
            self.sock.connect(( serverIP , portNum ))
            self.sock.settimeout(None)
            devAvail = 1
          except:
            devAvail = -1
          while  devAvail == 1 and self.sock <> None:
            time.sleep(0.01)
            try:
              data = self.sock.recv(1024)
              #print json.read(data)
	      print data

            except:
	      print 'closing socket'  
              self.sock.close()
              break

class PTmpCreate (ProcessEvent):
	def process_IN_CREATE(self, event):
		if   (event.name[0:9] == "powermate")  and (event.path == "/tmp/tangibles") :
			this = event.path + "/" + event.name
			newDevice.put (this)
			pass
                  
def newDev(path):
	notifier = Notifier(wm, PTmpCreate())
	wdd = wm.add_watch(path, maskCreate, rec=True)
	while True:  # loop forever
		time.sleep(0.1)
		try:
			notifier.process_events()
			if notifier.check_events():
				notifier.read_events()
		except KeyboardInterrupt:
			notifier.stop()
			break

newDevice = Queue.Queue (0)
#for i in range(30):
  #if (os.path.exists('/tmp/tangibles/powermate%s'%i)):
    #newDevice.put('/tmp/tangibles/powermate%s'%i)
pmate = powermateEvent()
pmate.start()
#newDev('/tmp/tangibles')
while 1:
  try:
    time.sleep(1)
  except KeyboardInterrupt:
    pmate.quit()
    sys.exit()
  
if __name__ == "__main__":
  print "exiting"
  exit()

