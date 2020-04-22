"""
Support for Nespresso Connected mmachine.
https://www.nespresso.com

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.Nespresso/
"""
import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (ATTR_DEVICE_CLASS, ATTR_ICON, CONF_MAC,
                                 CONF_NAME, CONF_SCAN_INTERVAL,
                                 CONF_UNIT_SYSTEM, DEVICE_CLASS_TEMPERATURE,
                                 DEVICE_CLASS_TIMESTAMP,
                                 EVENT_HOMEASSISTANT_STOP, STATE_UNKNOWN,
                                 TEMP_CELSIUS, TEMPERATURE)
from homeassistant.helpers.entity import Entity

from .nespresso import NespressoDetect

_LOGGER = logging.getLogger(__name__)
CONNECT_TIMEOUT = 30
SCAN_INTERVAL = timedelta(seconds=300)

ATTR_RADON_LEVEL = 'radon_level'
DEVICE_CLASS_RADON='radon'

DEVICE_CLASS_CAPS='caps'
CAPS_UNITS = 'caps'

DOMAIN = 'Nespresso'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_MAC, default=''): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
})


class Sensor:
    def __init__(self, unit, unit_scale, device_class, icon):
        self.unit = unit
        self.unit_scale = unit_scale
        self.device_class = device_class
        self.icon = icon

    def set_unit_scale(self, unit, unit_scale):
        self.unit = unit
        self.unit_scale = unit_scale

    def get_extra_attributes(self, data):
        return {}


DEVICE_SENSOR_SPECIFICS = { "State":Sensor('State', None, None, None),
                            "water_hardness":Sensor(TEMP_CELSIUS, None, DEVICE_CLASS_TEMPERATURE, None),
                            "caps_number": Sensor(CAPS_UNITS, None, DEVICE_CLASS_CAPS, 'mdi:thermometer-alert'),
                           }


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Nespresso sensor."""
    scan_interval = config.get(CONF_SCAN_INTERVAL).total_seconds()
    mac = config.get(CONF_MAC)
    mac = None if mac == '' else mac

    _LOGGER.debug("Searching for Nespresso sensors...")
    Nespressodetect = NespressoDetect(scan_interval, mac)
    try:
        if mac is None:
            num_devices_found = Nespressodetect.find_devices()
            _LOGGER.info("Found {} Nespresso device(s)".format(num_devices_found))

        if mac is None and num_devices_found == 0:
            _LOGGER.warning("No Nespresso devices found.")
            return

        _LOGGER.debug("Getting info about device(s)")
        devices_info = Nespressodetect.get_info()
        for mac, dev in devices_info.items():
            _LOGGER.info("{}: {}".format(mac, dev))

        _LOGGER.debug("Getting sensors")
        devices_sensors = Nespressodetect.get_sensors()
        for mac, sensors in devices_sensors.items():
            for sensor in sensors:
                _LOGGER.debug("{}: Found sensor UUID: {} Handle: {}".format(mac, sensor.uuid, sensor.handle))

        _LOGGER.debug("Get initial sensor data to populate HA entities")
        ha_entities = []
        sensordata = Nespressodetect.get_sensor_data()
        for mac, data in sensordata.items():
            for name, val in data.items():
                _LOGGER.debug("{}: {}: {}".format(mac, name, val))
                ha_entities.append(NespressoSensor(mac, name, Nespressodetect, devices_info[mac],
                                                   DEVICE_SENSOR_SPECIFICS[name]))
    except:
        _LOGGER.exception("Failed intial setup.")
        return

    add_entities(ha_entities, True)


class NespressoSensor(Entity):
    """General Representation of an Nespresso sensor."""
    def __init__(self, mac, name, device, device_info, sensor_specifics):
        """Initialize a sensor."""
        self.device = device
        self._mac = mac
        self._name = '{}-{}'.format(mac, name)
        _LOGGER.debug("Added sensor entity {}".format(self._name))
        self._sensor_name = name

        self._device_class = sensor_specifics.device_class
        self._state = STATE_UNKNOWN
        self._sensor_specifics = sensor_specifics

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._sensor_specifics.icon

    @property
    def device_class(self):
        """Return the icon of the sensor."""
        return self._sensor_specifics.device_class

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._sensor_specifics.unit

    @property
    def unique_id(self):
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        attributes = self._sensor_specifics.get_extra_attributes(self._state)
        return attributes

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self.device.get_sensor_data()
        value = self.device.sensordata[self._mac][self._sensor_name]
        if self._sensor_specifics.unit_scale is None:
            self._state = value
        else:
            self._state = round(float(value * self._sensor_specifics.unit_scale), 2)
        _LOGGER.debug("State {} {}".format(self._name, self._state))
