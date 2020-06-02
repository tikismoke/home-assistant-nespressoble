#!/usr/bin/env python3
from __future__ import print_function

import binascii
import ctypes
import struct
import time
from uuid import UUID

import paho.mqtt.client as paho
import pygatt

c_uint8 = ctypes.c_uint8

global device
#device = None
oldvalue = None
device= None
# Nespresso bluetooth MAC address
YOUR_DEVICE_ADDRESS = "XX:XX:XX:XX:XX:XX"
# Nespresso Apps secret code (you nedd to sniff it to find it)
# Replace XX by value (it's in hex format)
#AUTH_CODE = [0xXX, 0xXX,0xXX,0xXX,0xXX,0xXX,0xXX,0xXX]

YOUR_DEVICE_ADDRESS = "d2:12:f1:7b:cd:6d"
AUTH_CODE = [0x82, 0x87,0xee,0x82,0x59,0x3d,0x3c,0x4e]

# MQTT Broker IP or Name
broker="mosquito"
# MQTT Broker port
port=1883
STATUSTOPIC = "/nespresso/status"

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

def on_connect(client, userdata, flags, return_code):
	print("on_connect return_code: " + str(return_code))
	if return_code == 0:
		print("Connected to [%s]:[%s]" % (broker, port))
		client1.publish(STATUSTOPIC, "CONNECTED", retain=True)
	elif return_code == 1:
		print("Connection refused - unacceptable protocol version")
	elif return_code == 2:
		print("Connection refused - identifier rejected")
	elif return_code == 3:
		print("Connection refused - server unavailable")
		print("Retrying in 10 seconds")
		time.sleep(10)
	elif return_code == 4:
		print("Connection refused - bad user name or password")
	elif return_code == 5:
		print("Connection refused - not authorised")
	else:
		print("Something went wrong. RC:" + str(return_code))

# Define callbacks
client1= paho.Client("nespresso2mqtt")                           #create client object
client1.on_publish = on_publish                          #assign function to callback
client1.on_connect = on_connect
client1.on_message = on_message
client1.on_disconnect = on_disconnect
client1.subscribe("/Nespresso/#", 0)
client1.connect(broker,port)                                 #establish connection

client1.loop_start()

def printIndication(handle, value):
    print('Indication received {} : {}'.format(hex(handle), binascii.hexlify(str(value))))

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
            print(serv)
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
    try:
        # try:
        #     value = device.
        #     print("RSSI %s" % value)
        # except:
        #     print ("Get RSSI error")

        value = device.char_read("06aa3a12-f22a-11e3-9daa-0002a5d5c51b")
        if oldvalue != value:
            print("Etat %s" % (binascii.hexlify(value)))
            print (value)
            print (bin(int.from_bytes(value,byteorder='big')).strip('0b'))

            print (bin(value[0]))
            BYTE.asByte = value[0]
            print( "water_is_empty: %i"      % BYTE.bit0)
            try:
                client1.publish("/nespresso/state/water_empty", BYTE.bit0)
            except:
                print ("error publishing this value")
            print( "Descaled needed:  %i" % BYTE.bit2)
            try:
                client1.publish("/nespresso/state/descaled_needed", BYTE.bit2)
            except:
                print ("error publishing this value")
            print( "capsule_mechanism_jammed:  %i" % BYTE.bit4)
            try:
                client1.publish("/nespresso/state/capsule_mechanism_jammed", BYTE.bit4)
            except:
                print ("error publishing this value")
            print( "always_1 :  %i" % BYTE.bit6)
            try:
                client1.publish("/nespresso/state/always_1", BYTE.bit6)
            except:
                print ("error publishing this value")

            print (bin(value[1]))
            BYTE.asByte = value[1]
            print("water temp_low:  %i" % BYTE.bit0)
            try:
                client1.publish("/nespresso/state/water_temp_low", BYTE.bit0)
            except:
                print ("error publishing this value")
            print("awake: %i" % BYTE.bit1)
            try:
                client1.publish("/nespresso/state/awake", BYTE.bit1)
            except:
                print ("error publishing this value")
            print("water_engaged: %i" % BYTE.bit2)
            try:
                client1.publish("/nespresso/state/water_engadged", BYTE.bit2)
            except:
                print ("error publishing this value")
            print("sleeping %i" % BYTE.bit3)
            try:
                client1.publish("/nespresso/state/sleeping", BYTE.bit3)
            except:
                print ("error publishing this value")
            print("tray_sensor_tripped_during_brewing: %i" % BYTE.bit4)
            try:
                client1.publish("/nespresso/state/tray_sensor_during_brewing", BYTE.bit4)
            except:
                print ("error publishing this value")
            print("tray_open_tray_sensor_full: %i" % BYTE.bit6)
            try:
                client1.publish("/nespresso/state/tray_open_tray_sensor_full", BYTE.bit6)
            except:
                print ("error publishing this value")
            print("capsule_engaged: %i" % BYTE.bit7)
            try:
                client1.publish("/nespresso/state/capsule_engaged", BYTE.bit7)
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

            try:
                client1.publish("/nespresso/descaling_counter", int.from_bytes(value[6:9],byteorder='big'))
            except:
                print ("error publishing descale timer")

            trappe = device.char_read("06aa3a22-f22a-11e3-9daa-0002a5d5c51b")
            print("Read Slider %s" % (binascii.hexlify(trappe)))
            BYTE.asByte = trappe[0]
            print("Slider closed?:  %i" % BYTE.bit1)
            try:
                if (binascii.hexlify(trappe)) == b'00':
                    client1.publish("/nespresso/slider","Open" )
                else :
                    client1.publish("/nespresso/slider","Closed" )
            except:
                print ("error publishing Slider")

            nb_capsule = device.char_read("06aa3a15-f22a-11e3-9daa-0002a5d5c51b")
            print("Nb capsule %s" % int.from_bytes(nb_capsule, byteorder='big'))
            try:
                client1.publish("/nespresso/caps_count", int.from_bytes(nb_capsule,byteorder='big'))
            except:
                print ("error publishing this value")

            answer = device.char_read("06aa3a52-f22a-11e3-9daa-0002a5d5c51b")
            print("answer %s" % (binascii.hexlify(answer)))
            try:
                client1.publish("/nespresso/answer", (binascii.hexlify(answer)))
            except:
                print ("error publishing this value answer")

            oldvalue = value
            time.sleep(2)
    except Exception as e:
        print ("error")
        print (e)
