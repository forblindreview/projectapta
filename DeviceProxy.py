#!/usr/bin/env python

#import zmq #bau -- seeing if I can remove
import time, threading, thread
import sys
import json
import uuid
import messageTypes
import servicesMessages
import TangibleEvents
from random import randint
prxy_id = ''
class DeviceProxy(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = False
        
    def run(self):
        pass
    
    def quit(self):
        self.running = False

def subscr_loop(threadname, sock, request_sock=None, topic=None):
    print threadname,": is now listening for messages..."
    try:
        while 1:
            #print 'top of the loop'
            msg = sock.recv()
            #print msg
            if topic is not None:
                msg = msg.lstrip(topic)
            evt = TangibleEvents.Event().fromJSONFormattedMessage(msg)
            
            print evt.__dict__
            #try:
            #    fields = msg.split(', ')
            #    print fields
            #    if fields[1] == "D":
            #        print 'requesting devices list'
            #        print requestDevicesList(request_sock)
            #except AttributeError:
            #    pass
                
            time.sleep(0.01)
            #print 'bottom of the loop'
    except KeyboardInterrupt:
        return

def requestDevicesList(sock):
    global prxy_id
    req = servicesMessages.requestAvailableDevicesList(prxy_id)
    sock.send(req)
    rep = sock.recv()
    return json.read(rep)

def requestProxy(sock):
    req = servicesMessages.requestProxyMessage(uuid.getnode())
    sock.send(req)
    rep = sock.recv()
    return json.read(rep)

def requestDeviceAddition(sock, proxy_id, dev_handle):
    req = servicesMessages.requestAddDeviceToProxy(proxy_id.__str__(), dev_handle)
    sock.send(req)
    rep = sock.recv()
    return json.read(rep)

def main(argv):
    ctx = zmq.Context(2,2,zmq.NOBLOCK)
    sock = zmq.Socket(ctx, zmq.REQ)
    
    sock.connect('tcp://127.0.0.1:10777')
    proxy_advert_req = 'proxy_advert::\x00'
        
    reply = requestProxy(sock)
    print reply
    print 'uuid length', reply[-1]
    prxy_id = uuid.UUID(reply[2])
    
    dev_list_reply = requestDevicesList(sock)
    dev_list = dev_list_reply[2]
    print dev_list_reply
    dev_list =  dev_list_reply[2]
    len = dev_list.__len__() - 1
    
    dev_handle = dev_list[randint(0,len)]
    dev_handle_reply = requestDeviceAddition(sock, prxy_id, dev_handle)
    print dev_handle_reply
    
    #topic = prxy_id.fields[0].__hex__()+'@\x00'
    topic = dev_handle+'\x00'
    print 'topic: ', topic
    #topic = 'foo\x00'
    sub_sock = zmq.Socket(ctx, zmq.SUB)
    sub_sock.setsockopt(zmq.SUBSCRIBE, topic)
    sub_sock.connect('tcp://127.0.0.1:10778')
    
    subscr_thr = thread.start_new_thread(subscr_loop, ('Subscriber', sub_sock, sock, topic))
    
    #try:
    #    while 1:
    #        print 'top of the loop'
    #        msg = sub_sock.recv()
    #        print msg
    #        time.sleep(0.1)
    #        print 'bottom of the loop'
    try:
        while 1:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print 'Now exiting ... Goodbye'
        sys.exit()
    
    
if __name__ == '__main__':
    main(sys.argv)
    
