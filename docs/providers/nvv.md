# NVV (Nordhessischer Verkehrsverbund)

NVV provides departures and trip planning for northern Hesse via the HAFAS `mgate.exe` gateway.

## Coverage Area

- Kassel (KVG tram and bus, RegioTram)
- Landkreise Kassel, Werra-Meißner, Schwalm-Eder, Waldeck-Frankenberg, Hersfeld-Rotenburg
- Regional trains in northern Hesse

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://auskunft.nvv.de/auskunft/bin/app/mgate.exe` |
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

1. Select **NVV — Nordhessen (Kassel)** as provider
2. Search for your stop (e.g. "Kassel Hauptbahnhof")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Kassel Hauptbahnhof
- Kassel Königsplatz
- Kassel-Wilhelmshöhe
- Fulda

## Features

- Real-time departures with delay in minutes
- Platform information
- Trip planning (HAFAS `TripSearch`), including real-time delays and transfers
- No API key required

!!! note "Unofficial access id"
    The access id comes from the operator's own app (via the public-transport/transport-apis catalogue). It is not an officially issued key and may be rotated by the operator at any time.
