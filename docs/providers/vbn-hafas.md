# VBN (HAFAS, ohne API Key)

VBN provides departures and trip planning for Bremen and Lower Saxony via the VBN HAFAS `mgate.exe` gateway — **without an API key**, unlike the VBN OTP / TRIAS providers.

## Coverage Area

- Bremen (BSAG tram and bus), Bremerhaven, Oldenburg, Delmenhorst
- Regional trains and buses in the VBN area
- Long-distance trains calling in the region

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://fahrplaner.vbn.de/bin/mgate.exe` |
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

1. Select **VBN — Bremen / Niedersachsen (ohne API Key)** as provider
2. Search for your stop (e.g. "Bremen Hbf")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Bremen Hbf
- Bremen Domsheide
- Oldenburg (Oldb) Hbf
- Bremerhaven Hbf

## Features

- Real-time departures with delay in minutes
- Platform information
- Trip planning (HAFAS `TripSearch`), including real-time delays and transfers
- No API key required

!!! note "Unofficial access id"
    The access id comes from the operator's own app (via the public-transport/transport-apis catalogue). It is not an officially issued key and may be rotated by the operator at any time.
