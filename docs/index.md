# openpublictransport

Real-time public transport departures for Home Assistant — 23 providers across Germany, Switzerland, Austria, Sweden, Ireland, and worldwide.

!!! tip "Coming from VRRAPI-HACS or hacs-publictransport?"
    This is the new official repository! The domain changed from `vrr` to `openpublictransport` — entity IDs and services have new names.
    
    **[→ Migration Guide](migration.md)** — Step-by-step instructions for both migrations.

## Supported Providers (23)

| Provider | Region | API Type | API Key |
|----------|--------|----------|---------|
| **VRR** | Rhein-Ruhr (NRW) | EFA | No |
| **KVV** | Karlsruhe | EFA | No |
| **HVV** | Hamburg | REST | No |
| **BVG** | Berlin / Brandenburg | REST | No |
| **MVV** | Munich | EFA | No |
| **VVS** | Stuttgart | EFA | No |
| **VGN** | Nuremberg | EFA | No |
| **VAG** | Freiburg | EFA | No |
| **RMV** | Frankfurt / Rhein-Main | HAFAS | Yes (free) |
| **VRN** | Rhein-Neckar | EFA | No |
| **VVO** | Dresden | EFA | No |
| **DING** | Ulm / Donau-Iller | EFA | No |
| **AVV** | Augsburg | EFA | No |
| **RVV** | Regensburg | EFA | No |
| **BSVG** | Braunschweig | EFA | No |
| **NWL** | Westfalen-Lippe | EFA | No |
| **NVBW** | Baden-Württemberg | EFA | No |
| **BEG** | Bavaria | EFA | No |
| **SBB** | Switzerland (nationwide) | EFA | No |
| **ÖBB** | Austria (nationwide) | EFA | No |
| **Trafiklab** | Sweden (nationwide) | REST | Yes (free) |
| **NTA** | Ireland (nationwide) | GTFS-RT | Yes (free) |
| **Transitous** | Worldwide (community) | MOTIS2 | No |

## Features

### Core Features

- **Smart Setup Wizard** - Intuitive multi-step configuration with autocomplete for locations and stops
- **Real-time Departures** - Shows current departure times with delays
- **Multiple Transport Types** - Supports trains (ICE, IC, RE), subway, trams, and buses
- **Smart Filtering** - Filter by specific transportation types
- **Binary Sensor for Delays** - Automatic detection of delays > 5 minutes
- **Device Support** - Entities are grouped together with suggested areas
- **Repair Issues Integration** - Automatic notifications for API errors or rate limits
- **Rate Limiting** - Intelligent API rate limiting to prevent overload
- **Timezone Support** - Proper handling of provider-specific timezones

### Intelligence & Performance Features

- **Fuzzy Matching with Typo Tolerance** - Intelligently finds stops even with typos
    - Handles common misspellings: "Hauptbanhof" → "Hauptbahnhof"
    - German umlaut normalization: "Dusseldorf" → "Düsseldorf"
- **API Response Caching** - 5-minute intelligent cache reduces API load
- **Optimized Sensor Performance** - 20-30% faster departure processing

## Quick Start

1. Install via HACS (recommended) or manually
2. Add the integration via **Settings** > **Devices & Services** > **Add Integration**
3. Search for "Public Transport Departures"
4. Follow the setup wizard to configure your stops

## Transportation Types

The integration supports the following transport types:

| Type | Icon | Description |
|------|------|-------------|
| `train` | :material-train: | Trains (ICE, IC, RE, RB) |
| `subway` | :material-subway-variant: | Subway/Metro (U-Bahn) |
| `tram` | :material-tram: | Tram/Streetcar |
| `bus` | :material-bus: | Bus |
| `ferry` | :material-ferry: | Ferry |
| `taxi` | :material-taxi: | Taxi |

## License

This project is licensed under the MIT License.

## Support

For issues or questions:

1. Check the [Troubleshooting](troubleshooting.md) guide
2. Search existing [GitHub Issues](https://github.com/NerdySoftPaw/openpublictransport/issues)
3. Create a new issue with debug information
