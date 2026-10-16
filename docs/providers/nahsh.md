# NAH.SH (Nahverkehrsverbund Schleswig-Holstein)

NAH.SH provides departures for Schleswig-Holstein, Germany via the modern HAFAS `mgate.exe` gateway.

## Coverage Area

- All of Schleswig-Holstein
- Kiel, Lübeck, Flensburg, Neumünster and the rural regions
- Regional trains, city and regional buses, ferries

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://nahsh.hafas.cloud/gate` |
| **API Key** | Not required (unsigned mgate; uses the access id of the operator's own app) |
| **Timezone** | Europe/Berlin |
| **Data Format** | HAFAS mgate (JSON) |

## Transport Types

| Category (catOut) | Type | Description |
|-------------------|------|-------------|
| ICE / IC / EC / RE / RB / S | train | Long-distance, regional and S-Bahn trains |
| STR / Tram | tram | Tram / Stadtbahn |
| Bus | bus | City and regional buses |
| Fähre / Schiff | ferry | Ferries |

## Configuration

### Setup Steps

1. Select **NAH.SH — Schleswig-Holstein** as provider
2. Search for your stop (e.g. "Kiel Hbf")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Kiel Hbf
- Lübeck Hbf
- Flensburg ZOB
- Neumünster Bahnhof

## Features

- Real-time departures with delay in minutes
- Platform information
- Cancellations
- No API key required
- Trip planning is not available for this provider

!!! note "Unofficial access id"
    The access id comes from the operator's own app (via the public-transport/transport-apis catalogue). It is not an officially issued key and may be rotated by the operator at any time.
