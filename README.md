# Heatpump Infrared — Home Assistant Custom Component

Control split-system heat pumps and air conditioners via IR blaster from Home Assistant. Protocols ported from the [arduino-heatpumpir](https://github.com/ToniA/arduino-heatpumpir) library.

## Supported models (47)

| Brand | Models |
|---|---|
| AUX | AUX |
| Airway | AIRWAY |
| Ballu | Ballu |
| BGH | AUD |
| Carrier | NQV, MCA |
| Daikin | ARC433B50, ARC417, ARC480 |
| Electrolux | YAL |
| Fuego | Fuego |
| Fujitsu | AWYZ (AR-PZ2) |
| Gree | Generic, YAN, YAA, YAC, YT |
| Hisense | AUD |
| Hitachi | — |
| Hyundai | — |
| IVT | AY-XP12FR-N |
| Midea | Ultimate Pro Plus |
| Mitsubishi Electric | FD, FE, MSY, FA, KJ, MSC, SEZ |
| Mitsubishi Heavy | ZJ, ZEA, ZM, FDTC |
| Nibe | — |
| Olimpia Splendid | Maestro |
| Panasonic | DKE, EKE, JKE, NKE, LKE, CKP |
| Philco | PHS32 |
| Samsung | AQV, FJM |
| Sharp | AY-ZP40KR |
| Toshiba | Standard, Daiseikai |

## Requirements

- Home Assistant 2024.1 or later
- The `infrared` integration enabled in Home Assistant (provides the IR blaster entity)
- An IR blaster device supported by HA (e.g. Broadlink RM, ESPHome with IR transmitter)

## Installation

### HACS (recommended)

1. In HACS, go to **Integrations** → click the three-dot menu → **Custom repositories**
2. Add `https://github.com/feiming/homeassistant-heatpump` and select category **Integration**
3. Click **Download** on the **Heatpump Infrared** card
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/heatpump_infrared` directory into your HA config folder:

```
<config>/
└── custom_components/
    └── heatpump_infrared/
        ├── __init__.py
        ├── climate.py
        ├── config_flow.py
        ├── const.py
        ├── manifest.json
        ├── strings.json
        ├── translations/
        ├── brand/
        └── ir/
```

2. Restart Home Assistant.

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Heatpump Infrared**
3. Select your heat pump brand and model from the dropdown
4. Select the IR blaster entity that will send the commands
5. Click **Submit** — a climate entity appears immediately

## Feedback temperature sensor (optional)

IR blasters are one-way — there's no confirmation the unit actually received or acted on a command. To get some visual feedback, you can point the climate entity at an external temperature sensor near the unit:

1. Go to **Settings → Devices & Services**, find the Heatpump Infrared entry, and click **Configure**
2. Select a temperature sensor entity (e.g. from a smart plug, thermostat, or standalone sensor)
3. Its reading is shown as the climate entity's current temperature, so you can watch the room respond after sending a command

Leave the field blank to disable this (the default).

## Usage

The integration creates a standard `climate` entity. Use it from the UI, automations, or scripts exactly like any other climate entity:

```yaml
service: climate.set_temperature
target:
  entity_id: climate.living_room_heatpump
data:
  temperature: 22
  hvac_mode: heat
```

Supported HVAC modes depend on the model but generally include: `off`, `heat`, `cool`, `dry`, `fan_only`.

## Troubleshooting

**Commands have no effect**
- Confirm the IR blaster entity is working (test it from Developer Tools → Services with `remote.send_command`)
- Point the blaster directly at the unit's IR receiver
- Make sure you selected the correct model — some brands have multiple protocol variants (e.g. Daikin ARC433 vs ARC417 vs ARC480)

**My model is not listed**
- Open an issue with the brand/model name and, if possible, a link to the remote control part number
- The protocols are ported from [arduino-heatpumpir](https://github.com/ToniA/arduino-heatpumpir); if your model is there but missing here, PRs are welcome

## Development

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run the test suite (no Home Assistant install required)
pytest
```

Tests cover all 47 models: correct command generation, timing alternation, 38 kHz modulation, and protocol-specific frame structure.

## Credits

IR protocols ported from [ToniA/arduino-heatpumpir](https://github.com/ToniA/arduino-heatpumpir) (GPL-2.0).

## License

GPL-2.0, inherited from the upstream arduino-heatpumpir project. See [LICENSE](LICENSE).
