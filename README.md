# HA LCDproc Client V2

Modern LCDproc client add-on for Home Assistant.

## Basic configuration

```yaml
lcdproc_host: "192.168.88.206"
lcdproc_port: 13666
lcd_width: 16
lcd_height: 2
rotation_seconds: 5
refresh_seconds: 2
debug: false
screens:
  - name: "Cisterna"
    entity: "sensor.nivel_cisterna"
    decimals: 0
    progressbar: true
  - name: "Exterior"
    entity: "sensor.alfa_clima_outside_temperature"
    decimals: 2
```
