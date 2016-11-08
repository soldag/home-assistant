"""
Support for Flux lights.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.flux_led/
"""
import logging
import socket
import random

import voluptuous as vol

from homeassistant.const import CONF_DEVICES, CONF_NAME
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ATTR_EFFECT, EFFECT_RANDOM,
    SUPPORT_BRIGHTNESS, SUPPORT_EFFECT, SUPPORT_RGB_COLOR, Light,
    PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['https://github.com/Danielhiversen/flux_led/archive/0.8.zip'
                '#flux_led==0.8']

_LOGGER = logging.getLogger(__name__)

CONF_AUTOMATIC_ADD = 'automatic_add'
CONF_RGBW = 'rgbw'

DOMAIN = 'flux_led'

SUPPORT_FLUX_LED = (SUPPORT_BRIGHTNESS | SUPPORT_EFFECT |
                    SUPPORT_RGB_COLOR)

DEVICE_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_DEVICES, default={}): {cv.string: DEVICE_SCHEMA},
    vol.Optional(CONF_AUTOMATIC_ADD, default=False):  cv.boolean,
    vol.Optional("rgbw", default=True):  cv.boolean,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Flux lights."""
    import flux_led
    lights = []
    light_ips = []
    for ipaddr, device_config in config[CONF_DEVICES].items():
        device = {}
        device['name'] = device_config[CONF_NAME]
        device['ipaddr'] = ipaddr
        device['rgbw'] = device_config[CONF_RGBW]
        light = FluxLight(device)
        if light.is_valid:
            lights.append(light)
            light_ips.append(ipaddr)

    if not config[CONF_AUTOMATIC_ADD]:
        add_devices(lights)
        return

    # Find the bulbs on the LAN
    scanner = flux_led.BulbScanner()
    scanner.scan(timeout=10)
    for device in scanner.getBulbInfo():
        ipaddr = device['ipaddr']
        if ipaddr in light_ips:
            continue
        device['name'] = device['id'] + " " + ipaddr
        device['rgbw'] = True
        light = FluxLight(device)
        if light.is_valid:
            lights.append(light)
            light_ips.append(ipaddr)

    add_devices(lights)


class FluxLight(Light):
    """Representation of a Flux light."""

    def __init__(self, device):
        """Initialize the light."""
        import flux_led

        self._name = device['name']
        self._ipaddr = device['ipaddr']
        self._rgbw = device['rgbw']
        self.is_valid = True
        self._bulb = None
        try:
            self._bulb = flux_led.WifiLedBulb(self._ipaddr)
        except socket.error:
            self.is_valid = False
            _LOGGER.error(
                "Failed to connect to bulb %s, %s", self._ipaddr, self._name)

    @property
    def unique_id(self):
        """Return the ID of this light."""
        return "{}.{}".format(self.__class__, self._ipaddr)

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._bulb.isOn()

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._bulb.getWarmWhite255()

    @property
    def rgb_color(self):
        """Return the color property."""
        return self._bulb.getRgb()

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_FLUX_LED

    def turn_on(self, **kwargs):
        """Turn the specified or all lights on."""
        if not self.is_on:
            self._bulb.turnOn()

        rgb = kwargs.get(ATTR_RGB_COLOR)
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        effect = kwargs.get(ATTR_EFFECT)
        if rgb:
            self._bulb.setRgb(*tuple(rgb))
        elif brightness:
            if self._rgbw:
                self._bulb.setWarmWhite255(brightness)
            else:
                (red, green, blue) = self._bulb.getRgb()
                self._bulb.setRgb(red, green, blue, brightness=brightness)
        elif effect == EFFECT_RANDOM:
            self._bulb.setRgb(random.randrange(0, 255),
                              random.randrange(0, 255),
                              random.randrange(0, 255))

    def turn_off(self, **kwargs):
        """Turn the specified or all lights off."""
        self._bulb.turnOff()

    def update(self):
        """Synchronize state with bulb."""
        self._bulb.refreshState()
