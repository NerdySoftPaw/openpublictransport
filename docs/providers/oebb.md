# ÖBB (Austrian Federal Railways)

ÖBB (Österreichische Bundesbahnen) provides access to Austrian public transport data through a FPTF-compatible REST API.

## Coverage Area

- All of Austria
- ÖBB (national and regional rail)
- Wiener Linien (Vienna metro, tram, bus)
- Regional operators (Postbus, Westbahn, etc.)

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://oebb.macistry.com/api` |
| **API Key** | Not required |
| **Timezone** | Europe/Vienna |
| **Data Format** | FPTF (Friendly Public Transport Format) |

## Transport Types

| Product | Type | Description |
|---------|------|-------------|
| nationalExpress | train | Railjet, ICE |
| national | train | IC, EC |
| interregional | train | IR trains |
| regional | train | REX, R trains |
| suburban | train | S-Bahn |
| subway | subway | U-Bahn (Vienna) |
| tram | tram | Tram/Straßenbahn |
| bus | bus | Bus services |
| ferry | ferry | Ferry |

## Configuration

### Setup Steps

1. Select **ÖBB -- Österreich** as provider
2. Search for your stop (e.g. "Wien Hauptbahnhof")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Wien Hauptbahnhof
- Graz Hauptbahnhof
- Salzburg Hbf
- Linz Hbf
- Innsbruck Hbf

## Features

- Realtime departure data with prognosis
- Delay information in minutes
- Platform information with change detection
- Service disruption notices from remarks
- Agency/operator info per departure
- No API key required

## API URLs

### Stop Search

```
https://oebb.macistry.com/api/locations?query=Wien%20Hauptbahnhof&results=15
```

### Departures

```
https://oebb.macistry.com/api/stops/STATION_ID/departures?results=10&duration=120
```
