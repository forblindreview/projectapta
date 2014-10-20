#!/usr/bin/env python

import OSC
import time, threading

client = OSC.OSCClient()
counter = 0
while counter < 10:
    msg = OSC.OSCMessage()
    msg.setAddress("/1/led5")
    msg.append(counter%2)
    client.sendto(msg, ('10.4.31.100', 9001))
    time.sleep(0.25)
    counter = counter + 1


receive_address = '10.4.28.210', 9000
send_address = '10.4.31.100', 9001

server = OSC.OSCServer(receive_address)

def print_handler(addr, tags, stuff, source):
    print '-------'
    print addr
    print tags
    print stuff
    print '-------'
toggle = 0
def toggle_handler(addr, tags, stuff, source):
    global toggle, client
    print 'toggle event'
    print addr
    print stuff
    #msg = OSC.OSCMessage()
    #msg.setAddress('/1/multitoggle2/1/1')
    #msg.append(toggle%2)
    #toggle = toggle + 1
    bundle = OSC.OSCBundle()
    for x in xrange(5,9):
        bundle.append( {'addr':'/1/led%d'%(x), 'args':[toggle%2] })
    client.send(bundle)
    toggle = toggle + 1

def main():
    global client
    message = OSC.OSCMessage()
    message.setAddress('/1/param 1')
    message.append('connected')
    client.send(message)
    server.addMsgHandler('default', print_handler)
    server.addMsgHandler('/1/multitoggle2/1/1', toggle_handler)
    server_thrd = threading.Thread( target = server.serve_forever )
    server_thrd.start()
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        message = OSC.OSCMessage()
        message.setAddress('/1/param 1')
        message.append('disconnected')
        client.send(message)
        server.close()
        server_thrd.join()
        print 'Done'

main()
