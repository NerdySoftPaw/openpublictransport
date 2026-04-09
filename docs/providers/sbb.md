# SBB (Swiss Federal Railways)

SBB (Schweizerische Bundesbahnen) provides access to all Swiss public transport data through the Swiss public transport API.

## Coverage Area

- All of Switzerland
- All regional transit operators
- SBB, BLS, SOB, Postauto, and local operators

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://transport.opendata.ch/v1` |
| **API Key** | Not required |
| **Timezone** | Europe/Zurich |

## Transport Types

| Category | Type | Description |
|----------|------|-------------|
| ICE, IC, IR, EC, RE, TGV, RJ | train | Long-distance and regional trains |
| S | train | S-Bahn |
| M | subway | Metro (Lausanne) |
| T | tram | Tram |
| B, NFB, BUS | bus | Bus services |
| BAT, FAE | ferry | Lake ferries |
| FUN | train | Funicular railways |

## Configuration

### Setup Steps

1. Select **SBB -- Schweiz** as provider
2. Search for your stop (e.g. "Zürich HB")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Zürich HB
- Bern
- Basel SBB
- Genève-Aéroport
- Luzern

## Features

- Full realtime departure data with prognosis
- Delay information in minutes
- Platform information with change detection
- All Swiss transport types supported
- No API key required

## API URLs

### Stop Search

```
https://transport.opendata.ch/v1/locations?query=Zürich%20HB&type=station
```

### Departures (Stationboard)

```
https://transport.opendata.ch/v1/stationboard?station=Zürich%20HB&limit=10
```
