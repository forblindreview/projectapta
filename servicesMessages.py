#!/usr/bin/env python

import json
from json import WriteException
from messageTypes import *

def requestProxyMessage(host):
    try:
        return json.write([REQ, REQUEST_PROXY, host])
    except WriteException:
        return None

def replyProxyMessage(proxy_id):
    try:
        return json.write([REPLY, REPLY_PROXY_ID, proxy_id])
    except WriteException:
        return None

def requestAvailableDevicesList(device_proxy_id):
    try:
        return json.write([REQ, REQUEST_AVAILABLE_DEVICES_LIST, device_proxy_id])
    except WriteException:
        return None

def replyAvailableDevicesList(devices_list):
    try:
        return json.write([REPLY, REPLY_AVAILABLE_DEVICES_LIST, devices_list])
    except WriteException:
       return None
    
def requestAddDeviceToProxy(device_proxy_id, device_handle):
    try:
        return json.write([REQ, REQUEST_ADD_DEVICE_TO_PROXY, device_proxy_id, device_handle])
    except WriteException:
       return None

def replyDeviceAddedToProxy(proxy_id, device_handle):
    try:
        return json.write([REPLY, REPLY_DEVICE_ADDED_TO_PROXY, proxy_id, device_handle])
    except WriteException:
       return None
    
def requestRemoveDeviceFromProxy(proxy_id, device_handle):
    try:
        return json.write([REQ, REQUEST_REMOVE_DEVICE_FROM_PROXY, proxy_id, device_handle])
    except WriteException:
       return None

def replyDeviceRemovedFromProxy(device_handle, proxy_id):
    try:
        return json.write([REPLY, REPLY_DEVICE_REMOVED_FROM_PROXY, proxy_id, device_handle])
    except WriteException:
       return None
    
def errorMessage(error_msg):
    try:
        return json.write([ERROR, error_msg])
    except WriteException:
        return None
