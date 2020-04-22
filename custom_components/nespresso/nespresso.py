import logging
import struct
import time
from collections import namedtuple
from datetime import datetime
from uuid import UUID

import pygatt
from pygatt.exceptions import BLEError, NotConnectedError, NotificationTimeout

_LOGGER = logging.getLogger(__name__)

AUTH_CODE = [0x82, 0x87,0xee,0x82,0x59,0x3d,0x3c,0x4e]

# Use full UUID since we do not use UUID from bluepy.btle
CHAR_UUID_DEVICE_NAME = UUID('00002a00-0000-1000-8000-00805f9b34fb')
CHAR_UUID_MANUFACTURER_NAME = UUID('00002a00-0000-1000-8000-00805f9b34fb')
CHAR_UUID_STATE = UUID('06aa3a12-f22a-11e3-9daa-0002a5d5c51b')
CHAR_UUID_NBCAPS = UUID('06aa3a15-f22a-11e3-9daa-0002a5d5c51b')
CHAR_UUID_SLIDER = UUID('06aa3a22-f22a-11e3-9daa-0002a5d5c51b')
CHAR_UUID_WATER_HARDNESS = UUID('06aa3a44-f22a-11e3-9daa-0002a5d5c51b')

Characteristic = namedtuple('Characteristic', ['uuid', 'name', 'format'])

manufacturer_characteristics = Characteristic(CHAR_UUID_MANUFACTURER_NAME, 'manufacturer', "utf-8")
device_info_characteristics = [manufacturer_characteristics,
                               Characteristic(CHAR_UUID_DEVICE_NAME, 'device_name', "utf-8")]

class NespressoDeviceInfo:
    def __init__(self, manufacturer='', serial_nr='', model_nr='', device_name=''):
        self.manufacturer = manufacturer
        self.serial_nr = serial_nr
        self.model_nr = model_nr
        self.device_name = device_name

    def __str__(self):
        return "Manufacturer: {} Model: {} Serial: {} Device:{}".format(
            self.manufacturer, self.model_nr, self.serial_nr, self.device_name)


sensors_characteristics_uuid = [CHAR_UUID_STATE, CHAR_UUID_NBCAPS, CHAR_UUID_SLIDER, CHAR_UUID_WATER_HARDNESS]

sensors_characteristics_uuid_str = [str(x) for x in sensors_characteristics_uuid]


class BaseDecode:
    def __init__(self, name, format_type, scale):
        self.name = name
        self.format_type = format_type
        self.scale = scale

    def decode_data(self, raw_data):
        val = struct.unpack(
            self.format_type,
            raw_data)
        if len(val) == 1:
            res = val[0] * self.scale
        else:
            res = val
        return {self.name:res}


class PlussDecode(BaseDecode):
    def decode_data(self, raw_data):
        val = super().decode_data(raw_data)
        val = val[self.name]
        data = {}
        data['date_time'] = str(datetime.isoformat(datetime.now()))
        data['humidity'] = val[1]/2.0
        data['radon_1day_avg'] = val[4] if 0 <= val[4] <= 16383 else None
        data['radon_longterm_avg'] = val[5] if 0 <= val[5] <= 16383 else None
        data['temperature'] = val[6]/100.0
        data['rel_atm_pressure'] = val[7]/50.0
        data['co2'] = val[8]*1.0
        data['voc'] = val[9]*1.0
        return data


sensor_decoders = {str(CHAR_UUID_STATE):BaseDecode(name="State", format_type='HHHHHHHHHHHHHHHHHH', scale=0),
                   str(CHAR_UUID_NBCAPS):BaseDecode(name="caps_number", format_type='HHHHHHHHHHHHHH', scale=0),
                   str(CHAR_UUID_SLIDER):BaseDecode(name="slider", format_type='H', scale=0),
                   str(CHAR_UUID_WATER_HARDNESS):BaseDecode(name="water_hardness", format_type='HHHHHHHH', scale=0),}


class NespressoDetect:
    def __init__(self, scan_interval, mac=None):
        self.adapter = pygatt.backends.GATTToolBackend()
        self.nespresso_devices = [] if mac is None else [mac]
        self.sensors = []
        self.sensordata = {}
        self.scan_interval = scan_interval
        self.last_scan = -1


    def find_devices(self):
        # Scan for devices and try to figure out if it is an Nespresso device.
        self.adapter.start(reset_on_start=False)
        devices = self.adapter.scan(timeout=3)
        self.adapter.stop()

        for device in devices:
            mac = device['address']
            _LOGGER.debug("connecting to {}".format(mac))
            try:
                self.adapter.start(reset_on_start=False)
                dev = self.adapter.connect(mac, address_type=pygatt.BLEAddressType.random)
                _LOGGER.debug("Connected")
                try:
                    data = dev.char_read(manufacturer_characteristics.uuid)
                    manufacturer_name = data.decode(manufacturer_characteristics.format)
                    if "Nespresso" in manufacturer_name.lower():
                        self.nespresso_devices.append(mac)
                except (BLEError, NotConnectedError, NotificationTimeout):
                    _LOGGER.debug("connection to {} failed".format(mac))
                finally:
                    dev.disconnect()
            except (BLEError, NotConnectedError, NotificationTimeout):
                _LOGGER.debug("Faild to connect")
            finally:
                self.adapter.stop()

        _LOGGER.debug("Found {} Nespresso devices".format(len(self.nespresso_devices)))
        return len(self.nespresso_devices)

    def get_info(self):
        # Try to get some info from the discovered Nespresso devices
        self.devices = {}

        for mac in self.nespresso_devices:
            device = NespressoDeviceInfo(serial_nr=mac)
            try:
                self.adapter.start(reset_on_start=False)
                dev = self.adapter.connect(mac, address_type=pygatt.BLEAddressType.random)
                for characteristic in device_info_characteristics:
                    try:
                        data = dev.char_read(characteristic.uuid)
                        setattr(device, characteristic.name, data.decode(characteristic.format))
                    except (BLEError, NotConnectedError, NotificationTimeout):
                        _LOGGER.exception("")
                dev.disconnect()
            except (BLEError, NotConnectedError, NotificationTimeout):
                _LOGGER.exception("")
            self.adapter.stop()
            self.devices[mac] = device

        return self.devices

    def get_sensors(self):
        self.sensors = {}
        for mac in self.nespresso_devices:
            try:
                self.adapter.start(reset_on_start=False)
                dev = self.adapter.connect(mac, address_type=pygatt.BLEAddressType.random)
                characteristics = dev.discover_characteristics()
                sensor_characteristics =  []
                for characteristic in characteristics.values():
                    _LOGGER.debug(characteristic)
                    if characteristic.uuid in sensors_characteristics_uuid_str:
                        sensor_characteristics.append(characteristic)
                self.sensors[mac] = sensor_characteristics
            except (BLEError, NotConnectedError, NotificationTimeout):
                _LOGGER.exception("Failed to discover sensors")

        return self.sensors

    def get_sensor_data(self):
        if time.monotonic() - self.last_scan > self.scan_interval:
            self.last_scan = time.monotonic()
            for mac, characteristics in self.sensors.items():
                try:
                    self.adapter.start(reset_on_start=False)
                    dev = self.adapter.connect(mac, address_type=pygatt.BLEAddressType.random)
                    characteristic = "06aa3a41-f22a-11e3-9daa-0002a5d5c51b"
                    dev.char_write(characteristic, bytearray(AUTH_CODE), wait_for_response=True) #your secret code
                    for characteristic in characteristics:
                        try:
                            data = dev.char_read_handle("0x{:04x}".format(characteristic.handle))
                            if characteristic.uuid in sensor_decoders:
                                _LOGGER.debug("{} data {}".format(mac, data))
                                #sensor_data = sensor_decoders[characteristic.uuid].decode_data(data)
                                sensor_data = data
                                _LOGGER.debug("{} Got sensordata {}".format(mac, sensor_data))
                                if self.sensordata.get(mac) is None:
                                    self.sensordata[mac] = sensor_data
                                else:
                                    self.sensordata[mac].update(sensor_data)
                        except (BLEError, NotConnectedError, NotificationTimeout):
                            _LOGGER.exception("Failed to read characteristic")

                    dev.disconnect()
                except (BLEError, NotConnectedError, NotificationTimeout):
                    _LOGGER.exception("Failed to connect")
                self.adapter.stop()

        return self.sensordata


if __name__ == "__main__":
    logging.basicConfig()
    _LOGGER.setLevel(logging.INFO)
    ad = NespressoDetect(180)
    num_dev_found = ad.find_devices()
    if num_dev_found > 0:
        devices = ad.get_info()
        for mac, dev in devices.items():
            _LOGGER.info("{}: {}".format(mac, dev))

        devices_sensors = ad.get_sensors()
        for mac, sensors in devices_sensors.items():
            for sensor in sensors:
                _LOGGER.info("{}: {}".format(mac, sensor))

        sensordata = ad.get_sensor_data()
        for mac, data in sensordata.items():
            for name, val in data.items():
                _LOGGER.info("{}: {}: {}".format(mac, name, val))
