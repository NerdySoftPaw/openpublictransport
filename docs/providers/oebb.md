# ÖBB (Austrian Federal Railways)

ÖBB (Österreichische Bundesbahnen) provides Austrian public transport departures through ÖBB's own "Scotty" HAFAS web interface.

!!! note
    Earlier versions used a third-party REST backend (`oebb.macistry.com`) which was permanently suspended by its operator. Since `python-openpublictransport` 0.1.13 the provider talks to ÖBB's official infrastructure at `fahrplan.oebb.at` instead. See [issue #50](https://github.com/NerdySoftPaw/openpublictransport/issues/50).

## Coverage Area

- All of Austria
- ÖBB (national and regional rail)
- Wiener Linien (Vienna metro, tram, bus)
- Regional operators (Postbus, Westbahn, etc.)

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://fahrplan.oebb.at/bin` |
| **API Key** | Not required |
| **Timezone** | Europe/Vienna |
| **Data Format** | HAFAS Scotty (`ajax-getstop.exe` + `stboard.exe`) |

## Transport Types

| Category | Type | Description |
|----------|------|-------------|
| RJ / RJX / ICE | train | Railjet, ICE |
| IC / EC / NJ / EN | train | InterCity, EuroCity, Nightjet |
| REX / CJX / R | train | Regional express / regional |
| S | train | S-Bahn |
| U | subway | U-Bahn (Vienna) |
| Tram | tram | Tram/Straßenbahn |
| Bus / O-Bus | bus | Bus / trolleybus |

## Configuration

### Setup Steps

1. Select **ÖBB -- Österreich** as provider
2. Search for your stop (e.g. "Wien Hauptbahnhof")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Wien Hbf
- Graz Hauptbahnhof
- Salzburg Hbf
- Linz Hbf
- Innsbruck Hbf

## Features

- Realtime departure data with delay in minutes
- Platform information with change detection
- Cancellations and service disruption notices (HIM messages)
- No API key required
