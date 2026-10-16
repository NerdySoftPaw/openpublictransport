# VAO (Verkehrsauskunft Österreich)

VAO provides departures and trip planning for **all of Austria** — every regional network (VOR, OÖVV, Steirischer Verkehrsverbund, VVT, Salzburg, VMOBIL, Kärnten) and ÖBB — via the Verbundlinie HAFAS `mgate.exe` gateway. Compared with the ÖBB provider it adds trip planning.

## Coverage Area

- All Austrian federal states, city and regional transport
- ÖBB long-distance and regional trains
- Trams and buses in Vienna, Graz, Linz, Innsbruck, Salzburg, Klagenfurt

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://verkehrsauskunft.verbundlinie.at/hamm/gate` |
| **API Key** | Not required |
| **Timezone** | Europe/Vienna |
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

1. Select **VAO — Österreich (alle Verkehrsverbünde)** as provider
2. Search for your stop (e.g. "Graz Jakominiplatz")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Graz Jakominiplatz
- Wien Hauptbahnhof
- Innsbruck Hauptbahnhof
- Linz/Donau Hauptplatz

## Features

- Real-time departures with delay in minutes
- Platform information
- Trip planning (HAFAS `TripSearch`), including real-time delays and transfers
- No API key required

!!! note "Unofficial access id"
    The access id comes from the operator's own app (via the public-transport/transport-apis catalogue). It is not an officially issued key and may be rotated by the operator at any time.

!!! note
    For Vienna, the [Wiener Linien](wienerlinien.md) provider has more complete real-time data for U-Bahn, trams and buses.
