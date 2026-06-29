# HA Display Hub Client

Home Assistant add-on that sends entity values to one or more Display Hub servers.

## Features

- Multiple displays
- Multiple screens per display
- Automatic rotation
- Scrolling text
- Progress bars
- Needle bars
- Native Home Assistant API
- TCP/JSON protocol

## Example configuration

```yaml
displayhub_host: "192.168.88.108"
displayhub_port: 4510

screens:
  - display: rack1
    name: Exterior
    entity: sensor.alfa_clima_outside_temperature
    decimals: 1

  - display: rack2
    name: Cisterna
    entity: sensor.nivel_cisterna
    progressbar: true
    bar_style: percent
    bar_min: 0
    bar_max: 100
```

## Requires

- HA Display Hub Server
