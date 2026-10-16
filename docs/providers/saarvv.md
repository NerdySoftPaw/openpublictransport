# saarVV (Saarländischer Verkehrsverbund)

saarVV provides departures for Saarland, Germany via the modern HAFAS `mgate.exe` gateway.

## Coverage Area

- All of Saarland
- Saarbrücken (Saarbahn and bus), Saarlouis, Neunkirchen, Homburg
- Regional trains and buses across the state

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://saarfahrplan.de/bin/mgate.exe` |
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

1. Select **saarVV — Saarland** as provider
2. Search for your stop (e.g. "Saarbrücken Hbf")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Saarbrücken Hbf
- Saarbrücken, Johanneskirche
- ZOB Kleiner Markt, Saarlouis
- Homburg (Saar) Hbf

## Features

- Real-time departures with delay in minutes
- Platform information
- Cancellations
- No API key required
- Trip planning (HAFAS `TripSearch`), including real-time delays and transfers

!!! note "Unofficial access id"
    The access id comes from the operator's own app (via the public-transport/transport-apis catalogue). It is not an officially issued key and may be rotated by the operator at any time.
