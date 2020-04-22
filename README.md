# nespresso

Simple Nespresso Ble coffee machine integrations


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