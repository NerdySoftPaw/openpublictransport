# Wiener Linien (Wien)

Wiener Linien provides real-time departures for Vienna's U-Bahn, trams and buses from the official open data API (no API key).

## Coverage Area

- U-Bahn lines U1–U6
- All Vienna tram and bus lines, night buses
- Badner Bahn (WLB) at Wiener Linien stops

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://www.wienerlinien.at/ogd_realtime/monitor` |
| **API Key** | Not required |
| **Timezone** | Europe/Vienna |
| **Data Format** | Wiener Linien OGD |

## Configuration

### Setup Steps

1. Select **Wiener Linien — Österreich (Wien)** as provider
2. Search for your stop (e.g. "Stephansplatz")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Stephansplatz
- Karlsplatz
- Schwedenplatz
- Westbahnhof

## Features

- Real-time departures with delay in minutes
- Platform information
- No API key required

!!! note
    Data source: Stadt Wien – data.wien.gv.at (CC BY 4.0). One stop covers the whole station with all its platforms.
