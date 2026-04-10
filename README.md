![logo]

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

Real-time public transport departures for Home Assistant — 23 providers across Germany, Switzerland, Austria, Sweden, Ireland, and worldwide.

**Website**: [openpublictransport.net](https://openpublictransport.net) | **Docs**: [docs.openpublictransport.net](https://docs.openpublictransport.net/)

> **Coming from VRRAPI-HACS or hacs-publictransport?**
> The domain changed from `vrr` to `openpublictransport` — entity IDs and services have new names.
> See the [Migration Guide](https://docs.openpublictransport.net/migration/) for step-by-step instructions.

## Supported Providers (23)

| Provider | Region | API Key |
|----------|--------|---------|
| **VRR** | Rhein-Ruhr (NRW) | No |
| **KVV** | Karlsruhe | No |
| **HVV** | Hamburg | No |
| **BVG** | Berlin / Brandenburg | No |
| **MVV** | Munich | No |
| **VVS** | Stuttgart | No |
| **VGN** | Nuremberg | No |
| **VAG** | Freiburg | No |
| **RMV** | Frankfurt | Yes (free) |
| **VRN** | Rhein-Neckar | No |
| **VVO** | Dresden | No |
| **DING** | Ulm | No |
| **AVV** | Augsburg | No |
| **RVV** | Regensburg | No |
| **BSVG** | Braunschweig | No |
| **NWL** | Westfalen-Lippe | No |
| **NVBW** | Baden-Württemberg | No |
| **BEG** | Bavaria | No |
| **SBB** | Switzerland (nationwide) | No |
| **ÖBB** | Austria (nationwide) | No |
| **Trafiklab** | Sweden (nationwide) | Yes (free) |
| **NTA** | Ireland (nationwide) | Yes (free) |
| **Transitous** | Worldwide (community) | No |

## Features

- **Real-time departures** with delay tracking, platform changes, and disruption notices
- **23 transit providers** — most require no API key
- **Trip planner** — A-to-B routes with transfer risk assessment
- **7 entity types** — sensor, binary sensor, calendar, event, camera, trip sensor, statistics
- **4 services** — refresh_departures, plan_trip, check_delays, announce_departure (TTS)
- **Walking time** — hides departures you can't reach
- **Fuzzy stop search** — handles typos and umlaut variations
- **Line filtering & favorites** — show only the lines you use
- **Camera departure board** — classic yellow-on-black station display
- **7 languages** — DE, EN, FR, NL, PL, IT, SV
- **Custom Lovelace card** — [openpublictransport-card](https://github.com/NerdySoftPaw/openpublictransport-card) with table, compact, and trip layouts

## Quick Start

### Install via HACS

1. Open **HACS** > **Integrations**
2. Click the three dots > **Custom repositories**
3. Add: `https://github.com/NerdySoftPaw/openpublictransport` (category: Integration)
4. Search for "Public Transport Departures" and install
5. Restart Home Assistant

### Configure

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for "Public Transport Departures"
3. Pick your provider, search for your stop, done

No YAML needed. Setup takes under 2 minutes.

## Dashboard Card

Install the [openpublictransport-card](https://github.com/NerdySoftPaw/openpublictransport-card) via HACS for the best experience:

```yaml
type: custom:openpublictransport-card
entity: sensor.YOUR_STOP_HERE
layout: table  # or: compact, trip
```

## Services

```yaml
# Refresh departures
service: openpublictransport.refresh_departures

# Plan a trip
service: openpublictransport.plan_trip
data:
  provider: vrr
  origin: Hauptbahnhof
  origin_city: Düsseldorf
  destination: Hauptbahnhof
  destination_city: Köln

# Check delays
service: openpublictransport.check_delays
data:
  entity_id: sensor.YOUR_STOP_HERE
  delay_threshold: 5

# TTS announcement
service: openpublictransport.announce_departure
data:
  entity_id: sensor.YOUR_STOP_HERE
  index: 0
```

## Documentation

Full documentation at **[docs.openpublictransport.net](https://docs.openpublictransport.net/)**:

- [Configuration](https://docs.openpublictransport.net/configuration/)
- [Providers](https://docs.openpublictransport.net/providers/)
- [Sensors & Attributes](https://docs.openpublictransport.net/sensors/)
- [Services](https://docs.openpublictransport.net/services/)
- [Trip Planner](https://docs.openpublictransport.net/trip-planner/)
- [Dashboard Examples](https://docs.openpublictransport.net/dashboard/)
- [Automations](https://docs.openpublictransport.net/automations/)
- [Migration Guide](https://docs.openpublictransport.net/migration/)

## Contributing

Contributions welcome! Fork, branch, test, PR. See the [docs](https://docs.openpublictransport.net/) for architecture details.

## License

MIT License

<!-- Links -->
[releases-shield]: https://img.shields.io/github/release/NerdySoftPaw/openpublictransport.svg?style=for-the-badge
[releases]: https://github.com/NerdySoftPaw/openpublictransport/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/NerdySoftPaw/openpublictransport.svg?style=for-the-badge
[commits]: https://github.com/NerdySoftPaw/openpublictransport/commits/main
[license-shield]: https://img.shields.io/github/license/NerdySoftPaw/openpublictransport.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-NerdySoftPaw-blue.svg?style=for-the-badge
[hacsbadge]: https://img.shields.io/badge/HACS-Default-blue.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[logo]: img/logo.png
