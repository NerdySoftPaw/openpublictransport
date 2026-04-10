# openpublictransport

Real-time public transport departures for Home Assistant — 23 providers across Germany, Switzerland, Austria, Sweden, Ireland, and worldwide.

**Website**: [openpublictransport.net](https://openpublictransport.net) | **Docs**: [docs.openpublictransport.net](https://docs.openpublictransport.net/)

## Setup

1. Install via HACS or copy `custom_components/openpublictransport/` manually
2. Restart Home Assistant
3. Go to **Settings** > **Devices & Services** > **Add Integration**
4. Search for "Public Transport Departures"
5. Pick your provider, search for your stop, configure settings

No YAML needed. Setup takes under 2 minutes.

## Supported Providers (23)

**Germany (18):** VRR, KVV, HVV, BVG, MVV, VVS, VGN, VAG, RMV*, VRN, VVO, DING, AVV, RVV, BSVG, NWL, NVBW, BEG
**Switzerland:** SBB | **Austria:** ÖBB | **Sweden:** Trafiklab* | **Ireland:** NTA* | **Worldwide:** Transitous

*API key required (free)

## Features

- 7 entity types: sensor, binary sensor, calendar, event, camera, trip sensor, statistics
- 4 services: refresh_departures, plan_trip, check_delays, announce_departure
- Walking time, line filtering, favorites, fuzzy stop search, TTS announcements
- Custom Lovelace card with table, compact, and trip layouts
- 7 languages: DE, EN, FR, NL, PL, IT, SV

## Documentation

See [docs.openpublictransport.net](https://docs.openpublictransport.net/) for full documentation.
