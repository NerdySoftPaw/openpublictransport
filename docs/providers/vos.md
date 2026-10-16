# VOS (Verkehrsgemeinschaft Osnabrück)

VOS provides departures and trip planning for Osnabrück city and county via the HAFAS `mgate.exe` gateway.

## Coverage Area

- Osnabrück (Stadtwerke Osnabrück buses)
- Landkreis Osnabrück
- Regional trains calling in the area

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://fahrplan.vos.info/bin/mgate.exe` |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |
| **Data Format** | HAFAS mgate |

## Transport Types

| Category | Type |
|----------|------|
| ICE / IC / EC / RE / RB / S / Zug | train |
| U-Bahn | subway |
| STR / Tram / Straßenbahn | tram |
| Bus / SEV | bus |
| Schiff / Fähre | ferry |

## Configuration

### Setup Steps

1. Select **VOS — Osnabrück** as provider
2. Search for your stop (e.g. "Osnabrück Hbf")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Osnabrück Hbf
- Osnabrück Neumarkt
- Osnabrück Altstadt
- Georgsmarienhütte

## Features

- Real-time departures with delay in minutes
- Platform information
- Trip planning (HAFAS `TripSearch`), including real-time delays and transfers
- No API key required

!!! note "Unofficial access id"
    The access id comes from the operator's own app (via the public-transport/transport-apis catalogue). It is not an officially issued key and may be rotated by the operator at any time.
