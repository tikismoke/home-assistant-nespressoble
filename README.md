# nespresso

Simple Nespresso Ble coffee machine integrations
It's based on pygatt and need a bluetooth device ble compatible to read Nespresso information.

Note that you need to find your auth code from the officials apps.

It's much easy with reading thoses tutorials and example:

https://gist.github.com/farminf/94f681eaca2760212f457ac59da99f23

https://medium.com/@urish/reverse-engineering-a-bluetooth-lightbulb-56580fcb7546

Pygattl required bluez to be installed on the host

```
sudo apt install bluez
```

## Features
* Supports make a lungo coffee via service
* Supports reading lots of states
* Even more incoming

## Still under developpment
This conponent use the reversed one here: https://github.com/petergullberg/brewbutton .

It is completelly based on this integrations https://github.com/custom-components/sensor.airthings_wave .
Thank's to Marty for is creation.

## Sensor configuration

```
- platform: Nespresso
  mac: d2:12:f1:7b:cd:6d
  resource: 8287ee82593d3c4e
  scan_interval: 30
```

Where:
- `<mac>` must be replace by the bluetooth mac address of the machine
- `<resource>` is the auth code that you must have catch with bluetooth sniffing the apps
- `<scan_interval>` Optionnal scant interval in seconds (default=300)

It could look looks like this:

![Image of HASS](HA_integration.png)