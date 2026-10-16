# VSN (Verkehrsverbund Süd-Niedersachsen)

VSN provides departures and trip planning for southern Lower Saxony via the HAFAS `mgate.exe` gateway (signed requests).

## Coverage Area

- Göttingen (GöVB buses)
- Landkreise Göttingen, Northeim, Holzminden
- Regional trains in southern Lower Saxony

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://fahrplaner.vsninfo.de/hafas/mgate.exe` |
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

1. Select **VSN — Südniedersachsen (Göttingen)** as provider
2. Search for your stop (e.g. "Göttingen Bahnhof/ZOB")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Göttingen Bahnhof/ZOB
- Göttingen Gänseliesel
- Northeim (Han) Bahnhof
- Holzminden Bahnhof

## Features

- Real-time departures with delay in minutes
- Platform information
- Trip planning (HAFAS `TripSearch`), including real-time delays and transfers
- No API key required

!!! note "Unofficial access id"
    The access id comes from the operator's own app (via the public-transport/transport-apis catalogue). It is not an officially issued key and may be rotated by the operator at any time.
