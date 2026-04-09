# Transitous (Worldwide / MOTIS2)

!!! warning "Community Service"
    Transitous is operated by volunteers on a best-effort basis. It may be less reliable than direct provider APIs. For critical use cases, prefer the dedicated provider for your region.

Transitous provides worldwide public transport data through the MOTIS2 routing engine, aggregating GTFS and GTFS-RT feeds from transit agencies around the globe.

## Coverage Area

- Worldwide (aggregated GTFS/GTFS-RT data)
- Europe, North America, Asia, and more
- Coverage depends on available GTFS feeds

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://api.transitous.org/api` |
| **API Key** | Not required |
| **Timezone** | Per-stop (automatic) |
| **Data Format** | MOTIS2 JSON |

## Transport Types

| Mode | Type | Description |
|------|------|-------------|
| HIGHSPEED_RAIL | train | High-speed trains (ICE, TGV, etc.) |
| LONG_DISTANCE | train | Long-distance trains |
| REGIONAL_FAST_RAIL | train | Regional express trains |
| REGIONAL_RAIL | train | Regional trains |
| SUBURBAN | train | S-Bahn / suburban rail |
| SUBWAY | subway | Metro / U-Bahn |
| TRAM | tram | Tram / streetcar |
| BUS | bus | Bus services |
| COACH | bus | Coach / long-distance bus |
| FERRY | ferry | Ferry / water transport |
| FUNICULAR | train | Funicular railway |
| GONDOLA | train | Gondola / cable car |
| TROLLEYBUS | bus | Trolleybus |

## Features

- **Worldwide coverage** via aggregated GTFS/GTFS-RT data
- **Realtime delays** when available from GTFS-RT feeds
- **Platform changes** detected from scheduled vs. actual track
- **Cancellation detection** via `cancelled` / `tripCancelled` flags
- **Agency info** included per departure
- **Per-stop timezone** — times are automatically converted to the stop's local timezone

## Configuration

### Setup Steps

1. Select **Transitous -- Weltweit (Community, Beta)** as provider
2. Search for your stop (any stop worldwide)
3. Select the stop from the results
4. Configure departure count and filters

### Example Stops

- D-Holthausen (Düsseldorf)
- Zürich HB (Switzerland)
- Wien Hauptbahnhof (Austria)
- London Paddington (UK)

## API URLs

### Stop Search (Geocode)

```
https://api.transitous.org/api/v1/geocode?text=Zürich%20HB&type=STOP
```

### Departures (StopTimes)

```
https://api.transitous.org/api/v5/stoptimes?stopId=STOP_ID&n=10
```

## Realtime Data

Realtime data availability depends on whether the underlying transit agency provides GTFS-RT feeds. When available, the `realTime` flag is set to `true` on individual departures.

## Troubleshooting

### No Results

If searches return no results:

- Try the full official stop name
- Try adding the city name (e.g. "Hauptbahnhof, Wien")
- Check that the stop exists in the [Transitous web interface](https://transitous.org)

### Missing Realtime Data

If departures show only scheduled times:

- The transit agency may not provide GTFS-RT feeds
- Realtime data may be temporarily unavailable
- Consider using the dedicated provider for your region if available
