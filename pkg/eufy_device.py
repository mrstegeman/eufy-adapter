"""Eufy adapter for Mozilla WebThings Gateway."""

from gateway_addon import Device
import threading
import time

from .eufy_property import EufyBulbProperty, EufySwitchProperty
from .util import MIN_TEMPERATURE, MAX_TEMPERATURE, relative_temp_to_kelvin


_POLL_INTERVAL = 5


class EufyDevice(Device):
    """Eufy device type."""

    def __init__(self, adapter, _id, name, eufy_dev):
        """
        Initialize the object.

        adapter -- the Adapter managing this device
        _id -- ID of this device
        name -- name of this device
        eufy_dev -- the lakeside device object to initialize from
        """
        Device.__init__(self, adapter, _id)
        self._type = []

        self.eufy_dev = eufy_dev
        self.description = eufy_dev.kind
        self.name = name
        if not self.name:
            self.name = self.description

        self.eufy_dev.connect()
        self.eufy_dev.update()

        t = threading.Thread(target=self.poll)
        t.daemon = True
        t.start()

    def poll(self):
        """Poll the device for changes."""
        while True:
            time.sleep(_POLL_INTERVAL)

            try:
                self.eufy_dev.update()
            except BrokenPipeError:
                try:
                    self.eufy_dev.connect()
                    self.eufy_dev.update()
                except OSError:
                    continue

            for prop in self.properties.values():
                prop.update()

    def is_on(self):
        """Determine whether or not the device is on."""
        return self.eufy_dev.power


class EufySwitch(EufyDevice):
    """Eufy smart switch/plug type."""

    def __init__(self, adapter, _id, name, eufy_dev):
        """
        Initialize the object.

        adapter -- the Adapter managing this device
        _id -- ID of this device
        name -- name of this device
        eufy_dev -- the lakeside device object to initialize from
        """
        EufyDevice.__init__(self, adapter, _id, name, eufy_dev)
        self._type.extend(['OnOffSwitch', 'SmartPlug'])

        self.properties['on'] = EufySwitchProperty(
            self,
            'on',
            {
                '@type': 'OnOffProperty',
                'title': 'On/Off',
                'type': 'boolean',
            },
            self.is_on()
        )


class EufyBulb(EufyDevice):
    """Eufy smart bulb type."""

    def __init__(self, adapter, _id, name, eufy_dev):
        """
        Initialize the object.

        adapter -- the Adapter managing this device
        _id -- ID of this device
        name -- name of this device
        eufy_dev -- the lakeside device object to initialize from
        """
        EufyDevice.__init__(self, adapter, _id, name, eufy_dev)
        self._type.extend(['OnOffSwitch', 'Light'])

        if self.is_color():
            self._type.append('ColorControl')

            self.properties['color'] = EufyBulbProperty(
                self,
                'color',
                {
                    '@type': 'ColorProperty',
                    'title': 'Color',
                    'type': 'string',
                },
                self.color()
            )

        if self.is_variable_color_temp():
            self._type.append('ColorControl')

            self.properties['colorTemperature'] = EufyBulbProperty(
                self,
                'colorTemperature',
                {
                    '@type': 'ColorTemperatureProperty',
                    'title': 'Color Temperature',
                    'type': 'integer',
                    'unit': 'kelvin',
                    'minimum': MIN_TEMPERATURE,
                    'maximum': MAX_TEMPERATURE,
                },
                self.color_temp()
            )

        if self.is_color() and self.is_variable_color_temp():
            self.properties['colorMode'] = EufyBulbProperty(
                self,
                'colorMode',
                {
                    '@type': 'ColorModeProperty',
                    'title': 'Color Mode',
                    'type': 'string',
                    'enum': [
                        'color',
                        'temperature',
                    ],
                    'readOnly': True,
                },
                self.color_mode()
            )

        self.properties['level'] = EufyBulbProperty(
            self,
            'level',
            {
                '@type': 'BrightnessProperty',
                'title': 'Brightness',
                'type': 'integer',
                'unit': 'percent',
                'minimum': 0,
                'maximum': 100,
            },
            self.brightness()
        )

        self.properties['on'] = EufyBulbProperty(
            self,
            'on',
            {
                '@type': 'OnOffProperty',
                'title': 'On/Off',
                'type': 'boolean',
            },
            self.is_on()
        )

    def is_color(self):
        """Determine whether or not the light is color-changing."""
        return self.eufy_dev.kind == 'T1013'

    def is_variable_color_temp(self):
        """Determine whether or not the light is color-temp-changing."""
        return self.eufy_dev.kind in ['T1012', 'T1013']

    def color_temp(self):
        """Determine the current color temperature."""
        return relative_temp_to_kelvin(self.eufy_dev.temperature)

    def color(self):
        """Determine the current color of the light."""
        if not hasattr(self.eufy_dev, 'colors') or \
                self.eufy_dev.colors is None:
            return '#000000'

        return '#{:02X}{:02X}{:02X}'.format(*self.eufy_dev.colors)

    def color_mode(self):
        """Determine the current color mode."""
        if self.color() == '#000000':
            return 'temperature'

        return 'color'

    def brightness(self):
        """Determine the current brightness of the light."""
        return self.eufy_dev.brightness
