# Public Transport Integration for Home Assistant

A Home Assistant integration for real-time public transport departure information across multiple European transit networks.

!!! tip "Coming from VRRAPI-HACS?"
    This is the new official repository! Your existing configuration will be automatically preserved.
    
    **[→ Migration Guide](migration.md)** - Quick 5-minute migration from the old repository.

## Supported Providers

| Provider | Region | API Key Required |
|----------|--------|------------------|
| **VRR** | Verkehrsverbund Rhein-Ruhr (NRW, Germany) | No |
| **KVV** | Karlsruher Verkehrsverbund (Germany) | No |
| **HVV** | Hamburger Verkehrsverbund (Germany) | No |
| **Trafiklab** | Sweden (nationwide) | Yes (free) |
| **NTA** | National Transport Authority (Ireland) | Yes (free) |

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
