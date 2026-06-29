# HA Display Hub Client

![HA Display Hub Client](docs/banner.png)

**HA Display Hub Client** is a Home Assistant add-on that reads Home Assistant entities and sends formatted screens to one or more displays managed by **HA Display Hub Server**.

It is designed for setups where a Raspberry Pi controls several LCD displays in a rack, panel or dashboard.

---

## Features

- Home Assistant add-on
- Native Home Assistant API access
- Sends data to HA Display Hub over TCP/JSON
- Multiple physical displays
- Multiple rotating screens per display
- Text scrolling
- Progress bars
- Gauge / needle bars
- Layout-based rendering
- Compatible with 16x2 LCD displays

---

## Architecture

![Architecture](docs/architecture.png)

```text
Home Assistant
      |
      v
Display Hub Client Add-on
      |
      | TCP / JSON
      v
Raspberry Pi running HA Display Hub
      |
      +-- rack1 LCD
      +-- rack2 LCD
      +-- rack3 LCD
      +-- rack4 LCD
```

---

## Requirements

- Home Assistant OS or Supervised installation
- HA Display Hub Server running on the network
- One or more configured displays on the server

Server project:

- [HA Display Hub](https://github.com/nicocalvagna/ha-display-hub)

---

## Installation

Add this repository to Home Assistant add-on repositories:

```text
https://github.com/nicocalvagna/ha-displayhub-client
```

Then install:

```text
Display Hub Client
```

Start the add-on and configure the server address.

---

## Example configuration

```yaml
displayhub_host: "192.168.88.108"
displayhub_port: 4510
lcd_width: 16
lcd_height: 2
rotation_seconds: 5
refresh_seconds: 2
debug: false

screens:
  - display: rack1
    layout: value
    name: Exterior
    entity: sensor.alfa_clima_outside_temperature
    decimals: 1
    scroll: true

  - display: rack2
    layout: percent_bar
    name: Cisterna
    entity: sensor.nivel_cisterna
    decimals: 0
    bar_min: "0"
    bar_max: "100"

  - display: rack1
    layout: gauge
    name: Presion ATM
    entity: sensor.alfa_clima_outside_pressure
    decimals: 1
    unit: hPa
    bar_min: "980"
    bar_max: "1040"

  - display: rack1
    layout: dual_value
    name: Clima
    entity: sensor.alfa_clima_outside_temperature
    entity2: sensor.alfa_clima_humidity
    decimals: 1
```

---

## Available layouts

| Layout | Description |
|---|---|
| `value` | Shows title on line 1 and value on line 2 |
| `percent_bar` | Shows title and a percentage progress bar |
| `gauge` | Shows title and a needle-style gauge |
| `dual_value` | Shows two Home Assistant entities on the same 16x2 display |

---

## Layout examples

![Layouts](docs/layouts.png)

### Value

```text
Exterior
23.4 C
```

### Percent bar

```text
Cisterna
72% ########
```

### Gauge

```text
Presion ATM
------|---------
```

### Dual value

```text
Clima 23.4 C
56 %
```

---

## Add-on interface

![Add-on screen](docs/addon-screen.png)

---

## Dashboard concept

![Dashboard](docs/dashboard.png)

---

## Notes

- `widget` is kept for compatibility with early versions. Prefer `layout`.
- `display` must match the display ID configured in HA Display Hub Server.
- For bar and gauge layouts, define `bar_min` and `bar_max`.

---

## Roadmap

- [x] Display Hub protocol support
- [x] Multiple displays
- [x] Screen rotation
- [x] Progress bars
- [x] Gauge layout
- [x] Dual value layout
- [ ] Custom icons
- [ ] Backlight commands
- [ ] More layout presets
- [ ] 20x4 dashboard layout

---

## License

MIT
