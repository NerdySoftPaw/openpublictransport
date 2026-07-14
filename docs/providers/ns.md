# NS (Nederlandse Spoorwegen)

NS provides departures for the Netherlands through the legacy HAFAS "Scotty" web interface.

## Coverage Area

- All of the Netherlands
- NS national and regional rail (Intercity, Sprinter)
- International trains calling at Dutch stations (ICE, Nightjet, Eurostar)

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://hafas.bene-system.com/bin` |
| **API Key** | Not required |
| **Timezone** | Europe/Amsterdam |
| **Data Format** | HAFAS Scotty (`ajax-getstop.exe` + `stboard.exe`) |

## Transport Types

| Category | Type | Description |
|----------|------|-------------|
| IC | train | Intercity |
| SPR | train | Sprinter (regional) |
| ICE / EC / NJ | train | International / high-speed |
| Bus / Tram / U | bus / tram / subway | Connecting urban services where available |

## Configuration

### Setup Steps

1. Select **NS -- Niederlande** as provider
2. Search for your stop (e.g. "Amsterdam Centraal")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Amsterdam Centraal
- Rotterdam Centraal
- Utrecht Centraal
- Den Haag Centraal
- Eindhoven Centraal

## Features

- Realtime departure data with delay in minutes
- Platform information
- Service disruption notices (HIM messages)
- No API key required
