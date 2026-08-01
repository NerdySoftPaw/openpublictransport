![openpublictransport logo][logo]

# openpublictransport

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![HACS][hacsbadge]][hacs]
[![Documentation](https://img.shields.io/badge/docs-openpublictransport.net-blue.svg?style=for-the-badge)](https://docs.openpublictransport.net/)

![Project Maintenance][maintenance-shield]
[![HACS Validation](https://github.com/NerdySoftPaw/openpublictransport/actions/workflows/hacs.yaml/badge.svg)](https://github.com/NerdySoftPaw/openpublictransport/actions/workflows/hacs.yaml)
[![Code Quality](https://github.com/NerdySoftPaw/openpublictransport/actions/workflows/lint.yaml/badge.svg)](https://github.com/NerdySoftPaw/openpublictransport/actions/workflows/lint.yaml)
[![Tests](https://github.com/NerdySoftPaw/openpublictransport/actions/workflows/tests.yaml/badge.svg)](https://github.com/NerdySoftPaw/openpublictransport/actions/workflows/tests.yaml)

Real-time public transport departures for Home Assistant — 35 providers across Germany, Austria, Switzerland, the Netherlands, Luxembourg, Norway, Sweden, Ireland, the USA, and worldwide.

**Website**: [openpublictransport.net](https://openpublictransport.net) | **Docs**: [docs.openpublictransport.net](https://docs.openpublictransport.net/)

> **Coming from VRRAPI-HACS or hacs-publictransport?**
> The domain changed from `vrr` to `openpublictransport` — entity IDs and actions have new names.
> See the [Migration Guide](https://docs.openpublictransport.net/latest/migration/) for step-by-step instructions.

---

## Supported Providers (35)

| Provider | Region | API Key | Trip Planner |
|----------|--------|---------|--------------|
| **AVV** | Augsburg | No | Yes |
| **BART** | San Francisco, USA | No | No |
| **BEG** | Bavaria | No | Yes |
| **BSVG** | Braunschweig | No | No |
| **BVG** | Berlin / Brandenburg | No | No |
| **DART** | Des Moines, USA | No | No |
| **DB** | Germany (nationwide, community API) | No | No |
| **DING** | Ulm | No | Yes |
| **Entur** | Norway (nationwide) | No | No |
| **HVV** | Hamburg | No | Yes |
| **Irish Rail** | Ireland (nationwide) | No | No |
| **KVV** | Karlsruhe | No | Yes |
| **mobilitéit.lu** | Luxembourg (nationwide) | No | No |
| **MVV** | Munich | No | Yes |
| **NS** | Netherlands (nationwide) | No | No |
| **NTA** | Ireland (nationwide) | Yes (free) | No |
| **NVBW** | Baden-Württemberg | No | No |
| **NWL** | Westfalen-Lippe | No | No |
| **ÖBB** | Austria (nationwide) | No | No |
| **openpublictransport** | Germany (nationwide, GTFS.DE + GTFS-RT, community OTP2) | Yes ([request](https://openpublictransport.net/api-key)) | No |
| **OTP2 Custom** | Any OTP2 instance (self-hosted) | Optional | No |
| **RMV** | Frankfurt / Rhein-Main | Yes (free) | No |
| **RVV** | Regensburg | No | No |
| **SBB** | Switzerland (nationwide) | No | No |
| **TPG** | Geneva, Switzerland | No | No |
| **Trafiklab** | Sweden (nationwide) | Yes (free) | No |
| **Transitous** | Worldwide (community) | No | No |
| **VAG** | Freiburg | No | Yes |
| **VBN (OTP)** | Bremen / Niedersachsen | Yes (free) | Yes |
| **VBN (TRIAS)** | Bremen / Niedersachsen | Yes (free) | No |
| **VGN** | Nuremberg | No | Yes |
| **VRN** | Rhein-Neckar | No | No |
| **VRR** | Rhein-Ruhr (NRW) | No | Yes |
| **VVO** | Dresden | No | No |
| **VVS** | Stuttgart | No | Yes |

---

## Features

- **Real-time departures** with delay tracking, platform changes, and disruption notices
- **35 transit providers** — most require no API key
- **Trip planner** — A-to-B routes with transfer risk assessment
- **8 entity types**: sensor, binary sensor, calendar, event, camera, trip sensor, statistics, multi-stop
- **4 actions** — refresh_departures, plan_trip, check_delays, announce_departure (TTS)
- **Reconfigure without re-setup** — change your station anytime via ⚙️ → Reconfigure
- **Walking time** — hides departures you can't reach on foot
- **Fuzzy stop search** — handles typos and umlaut variations
- **Line & destination filtering & favorites** — show only the lines or directions you use
- **Departure board camera** — classic yellow-on-black station display
- **7 languages** — DE, EN, FR, NL, PL, IT, SV
- **Custom Lovelace card** — [openpublictransport-card](https://github.com/NerdySoftPaw/openpublictransport-card) with table, compact, and trip layouts

---

## Quick Start

### Install via HACS

1. Open **HACS** → **Integrations**
2. Search for **"OpenPublicTransport"** and click **Download**
3. Restart Home Assistant

### Configure

1. **Settings** → **Devices & Services** → **Add Integration**
2. Search for **"OpenPublicTransport"**
3. Pick your provider, search for your stop, done

No YAML needed. Setup takes under 2 minutes.

---

## Entities

Each configured stop creates a device with the following entities:

| Entity | Type | Enabled by default |
|--------|------|--------------------|
| Departures | Sensor | ✅ |
| Delays | Binary Sensor (diagnostic) | ✅ |
| Schedule | Calendar | ❌ |
| Disruptions | Event | ❌ |
| Board | Camera | ❌ |
| Punctuality | Sensor (diagnostic) | ❌ |

Calendar, event, camera, and punctuality entities are **disabled by default** to keep dashboards clean. Enable them individually via **Settings → Devices & Services → [your stop] → entities**.

---

## Dashboard Card

Install the [openpublictransport-card](https://github.com/NerdySoftPaw/openpublictransport-card) via HACS for the best experience:

```yaml
type: custom:openpublictransport-card
entity: sensor.your_stop_here
layout: table  # or: compact, trip
```

---

## Actions

```yaml
# Refresh departures manually
action: openpublictransport.refresh_departures

# Plan a trip (A → B)
action: openpublictransport.plan_trip
data:
  provider: vrr
  origin: Hauptbahnhof
  origin_city: Düsseldorf
  destination: Hauptbahnhof
  destination_city: Köln

# Check delays on a stop
action: openpublictransport.check_delays
data:
  entity_id: sensor.your_stop_here
  delay_threshold: 5

# TTS announcement (reads next departure aloud)
action: openpublictransport.announce_departure
data:
  entity_id: sensor.your_stop_here
  index: 0
```

---

## Automation Examples

```yaml
# Notify when your train is delayed
automation:
  trigger:
    - platform: state
      entity_id: binary_sensor.hbf_delays
      to: "on"
  action:
    - action: notify.mobile_app_phone
      data:
        message: "Delays at Hbf — check the app"

# Announce next departure at 7:30
automation:
  trigger:
    - platform: time
      at: "07:30:00"
  action:
    - action: openpublictransport.announce_departure
      data:
        entity_id: sensor.hbf_departures
        index: 0
```

---

## Documentation

Full documentation at **[docs.openpublictransport.net](https://docs.openpublictransport.net/)**:

- [Configuration](https://docs.openpublictransport.net/configuration/)
- [Providers](https://docs.openpublictransport.net/providers/)
- [Sensors & Attributes](https://docs.openpublictransport.net/sensors/)
- [Actions](https://docs.openpublictransport.net/services/)
- [Trip Planner](https://docs.openpublictransport.net/trip-planner/)
- [Dashboard Examples](https://docs.openpublictransport.net/dashboard/)
- [Automations](https://docs.openpublictransport.net/automations/)
- [Migration Guide](https://docs.openpublictransport.net/migration/)

---

## Contributing

Contributions welcome — fork, branch, test, PR.

```bash
pip install pytest pytest-homeassistant-custom-component pytest-asyncio aiofiles gtfs-realtime-bindings
pytest tests/ -v
```

---

## License

MIT License

## 💰 You can help me by Donating
  [![BuyMeACoffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/nerdysoftpaw) [![Ko-Fi](https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/nerdysoftpaw90) 

<!-- Badges -->
[releases-shield]: https://img.shields.io/github/release/NerdySoftPaw/openpublictransport.svg?style=for-the-badge
[releases]: https://github.com/NerdySoftPaw/openpublictransport/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/NerdySoftPaw/openpublictransport.svg?style=for-the-badge
[commits]: https://github.com/NerdySoftPaw/openpublictransport/commits/main
[license-shield]: https://img.shields.io/github/license/NerdySoftPaw/openpublictransport.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-NerdySoftPaw-blue.svg?style=for-the-badge
[hacsbadge]: https://img.shields.io/badge/HACS-Default-blue.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[logo]: brand/logo.png
