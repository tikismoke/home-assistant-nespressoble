#!/usr/bin/env python3
from __future__ import print_function

import binascii
import pygatt
import time
import struct
import paho.mqtt.client as paho
import ctypes
c_uint8 = ctypes.c_uint8

global device
#device = None
oldvalue = None
device= None
# Nespresso bluetooth MAC address
YOUR_DEVICE_ADDRESS = "XX:XX:XX:XX:XX:XX"
AUTH_CODE = [0xXX, 0xXX,0xXX,0xXX,0xXX,0xXX,0xXX,0xXX]
# MQTT Broker IP or Name
broker="mosquito"
# MQTT Broker port
port=1883

class Flags_bits( ctypes.LittleEndianStructure ):
     _fields_ = [
                 ("bit0",     c_uint8, 1 ),  # asByte & 1
                 ("bit1",     c_uint8, 1 ),  # asByte & 2
                 ("bit2",     c_uint8, 1 ),  # asByte & 4
                 ("bit3",     c_uint8, 1 ),  # asByte & 8
                 ("bit4",     c_uint8, 1 ),  # asByte & 16
                 ("bit5",     c_uint8, 1 ),  # asByte & 32
                 ("bit6",     c_uint8, 1 ),  # asByte & 64
                 ("bit7",     c_uint8, 1 ),  # asByte & 128
                ]

class Flags( ctypes.Union ):
     _anonymous_ = ("bit",)
     _fields_ = [
                 ("bit",    Flags_bits ),
                 ("asByte", c_uint8    )
                ]

def on_publish(client,userdata,result):             #create function for callback
    print("data published \n")
    pass

def on_disconnect(client, userdata, rc):
   print("Client Got Disconnected")
   if rc != 0:
       print("Unexpected MQTT disconnection. Will auto-reconnect")

   else:
       print("rc value:" + str(rc))

   try:
       print("Trying to Reconnect")
       client.connect(broker, port)
   except:
       print("Error in Retrying to Connect with Broker")

def on_message(mosq, obj, msg):
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

client1= paho.Client("nespresso2mqtt")                           #create client object
client1.on_publish = on_publish                          #assign function to callback
client1.on_disconnect = on_disconnect
client1.on_message = on_message
client1.connect(broker,port)                                 #establish connection
client1.subscribe("/Nespresso/#", 0)

def printIndication(handle, value):
    print('Indication received {} : {}'.format(hex(handle), hexlify(str(value))))

def handle_data(handle, value):
    """
    handle -- integer, characteristic read handle the data was received on
    value -- bytearray, the data returned in the notification
    """
    print("Received data %s" % (binascii.hexlify(value)))

def discover_service(device):
    for service in device.discover_characteristics():
        try:
            print("[%s]    Characteristic [%s]" % (YOUR_DEVICE_ADDRESS, service))
            serv= device.char_read(service)
            print("Read UUID %s: %s" % (service, binascii.hexlify(serv)))
            if service=="06aa3a22-f22a-11e3-9daa-0002a5d5c51b":
                print("Slider status")
            if service == "06aa3a12-f22a-11e3-9daa-0002a5d5c51b":
                print("status")
        except:
            print("Read error for UUID [%s]" % (service))

def connectble():
    try:
        return adapter.connect(YOUR_DEVICE_ADDRESS, address_type=ADDRESS_TYPE)
    except Exception as error:
        print (error)
        time.sleep(15) # Wait 15s before reconnect
        connectble()

def new_cofee(device):
#Make me a cofee
    characteristic = "06aa3a42-f22a-11e3-9daa-0002a5d5c51b"
    time.sleep(2)
    try:
        #device.char_write(characteristic, bytearray([0x03,0x05,0X07,0x04,0x00,0x00,0x00,0x00,0x00,0x02]))
        device.char_write(characteristic, bytearray([0x03,0x05,0X07,0x04,0x00,0x00,0x00,0x00,0x00,0x02]), wait_for_response=True)
    except Exception as error:
        print (error)
#        time.sleep(5) # Wait 5s before resendcommand
#        new_cofee(device)

def connectnespresso(device,tries=0):
    try:
        characteristic = "06aa3a41-f22a-11e3-9daa-0002a5d5c51b"
        device.char_write(characteristic, bytearray(AUTH_CODE), wait_for_response=True) #your secret code

#Subscribe to state change
#        device.subscribe("06aa3a12-f22a-11e3-9daa-0002a5d5c51b", callback=handle_data)
    except Exception as error:
        print("connect error")
        time.sleep(5) # wait 5s
        if tries < 3:
            print ("<3 write error")
            connectnespresso(device, tries+1) #resend write auth
        elif tries < 5:
            print ("<5 write error")
            connectble() #reconnect to machine
            connectnespresso(device, tries+1) #resend write auth
        else:
            print (">5 write error")
            raise error

ADDRESS_TYPE = pygatt.BLEAddressType.random
#adapter = pygatt.GATTToolBackend()
adapter = pygatt.backends.GATTToolBackend()
adapter.start()
device = connectble()
connectnespresso(device)

BYTE = Flags()

#discover_service(device)
#new_cofee(device)
while True:
    value = device.char_read("06aa3a12-f22a-11e3-9daa-0002a5d5c51b")
    if oldvalue != value:
        print("Etat %s" % (binascii.hexlify(value)))
        print (value)
        print (bin(int.from_bytes(value,byteorder='big')).strip('0b'))

        print (bin(value[0]))
        BYTE.asByte = value[0]
        print( "water_is_empty: %i"      % BYTE.bit0)
        try:
            client1.publish("/Nespresso/state/water_empty", BYTE.bit0)
        except:
            print ("error publishing this value")
        print( "Descaled needed:  %i" % BYTE.bit3)
        try:
            client1.publish("/Nespresso/state/descaled_needed", BYTE.bit3)
        except:
            print ("error publishing this value")
        print( "capsule_mechanism_jammed:  %i" % BYTE.bit4)
        try:
            client1.publish("/Nespresso/state/capsule_mechanism_jammed", BYTE.bit4)
        except:
            print ("error publishing this value")
        print( "always_1 :  %i" % BYTE.bit6)
        try:
            client1.publish("/Nespresso/state/always_1", BYTE.bit6)
        except:
            print ("error publishing this value")

        print (bin(value[1]))
        BYTE.asByte = value[1]
        print("water temp_low:  %i" % BYTE.bit0)
        try:
            client1.publish("/Nespresso/state/water_temp_low", BYTE.bit0)
        except:
            print ("error publishing this value")
        print("awake: %i" % BYTE.bit1)
        try:
            client1.publish("/Nespresso/state/awake", BYTE.bit1)
        except:
            print ("error publishing this value")
        print("water_engaged: %i" % BYTE.bit2)
        try:
            client1.publish("/Nespresso/state/water_engadged", BYTE.bit2)
        except:
            print ("error publishing this value")
        print("sleeping %i" % BYTE.bit3)
        try:
            client1.publish("/Nespresso/state/sleeping", BYTE.bit3)
        except:
            print ("error publishing this value")
        print("tray_sensor_tripped_during_brewing: %i" % BYTE.bit4)
        try:
            client1.publish("/Nespresso/state/tray_sensor_during_brewing", BYTE.bit4)
        except:
            print ("error publishing this value")
        print("tray_open_tray_sensor_full: %i" % BYTE.bit6)
        try:
            client1.publish("/Nespresso/state/tray_open_tray_sensor_full", BYTE.bit6)
        except:
            print ("error publishing this value")
        print("capsule_engaged: %i" % BYTE.bit7)
        try:
            client1.publish("/Nespresso/state/capsule_engaged", BYTE.bit7)
        except:
            print ("error publishing this value")

        print (bin(value[2]))

        print (bin(value[3]))
        BYTE.asByte = value[3]
        print("Fault:  %i" % BYTE.bit5)

        print (bin(value[4]))
        print (bin(value[5]))
        print (bin(value[6]))
        print (bin(value[7]))
  
        trappe = device.char_read("06aa3a22-f22a-11e3-9daa-0002a5d5c51b")
        print("Read Slider %s" % (binascii.hexlify(trappe)))
        BYTE.asByte = trappe[0]
        print("Slider closed?:  %i" % BYTE.bit1)
        try:
            if (binascii.hexlify(trappe)) == b'00':
                client1.publish("/Nespresso/Slider","Open" )
            else :
                client1.publish("/Nespresso/Slider","Closed" )
        except:
            print ("error publishing Slider")

        nb_capsule = device.char_read("06aa3a15-f22a-11e3-9daa-0002a5d5c51b")
        print("Nb capsule %s" % int.from_bytes(nb_capsule, byteorder='big'))
        try:
            client1.publish("/Nespresso/Nbcapsule", int.from_bytes(nb_capsule,byteorder='big'))
        except:
            print ("error publishing this value")
        oldvalue = value
        time.sleep(2)
