# openpublictransport (Deutschland, Community Server)

!!! info "Community Server"
    This provider uses a community-hosted OTP2 server at **api.openpublictransport.net**, backed by [gtfs.de](https://gtfs.de) data (CC 4.0, Germany-wide). An API key is required — [request one here](https://openpublictransport.net/api-key).

The `openpublictransport` provider gives you Germany-wide real-time departures for all transit modes — S-Bahn, U-Bahn, Bus, Tram, Regional, IC/ICE — from a single unified endpoint. Data is updated daily from gtfs.de and enriched with GTFS-RT realtime delays every 30 seconds from 25+ Verbünde.

## Coverage Area

- All of Germany (461 agencies, 437 000+ stops)
- Data source: [gtfs.de](https://gtfs.de) Germany Full feed (CC 4.0)
- Realtime: [realtime.gtfs.de](https://gtfs.de/de/realtime/) GTFS-RT (VRR, BSVG, NWL, MVV, S-Bahn Berlin, and more)

## API Details

| Property | Value |
|----------|-------|
| **Server** | `https://api.openpublictransport.net/otp/routers/default` |
| **API Type** | OTP2 GraphQL |
| **API Key** | Yes — [request free key](https://openpublictransport.net/api-key) |
| **Timezone** | Europe/Berlin |
| **Data Source** | gtfs.de CC 4.0 + GTFS-RT |

## Transport Types

| OTP2 Mode | Type | Description |
|-----------|------|-------------|
| RAIL | train | Regional and long-distance trains (RE, RB, IC, ICE) |
| SUBWAY | subway | U-Bahn |
| TRAM | tram | Tram / Straßenbahn |
| BUS | bus | All bus services |
| FERRY | ferry | Ferry |
| COACH | bus | Coach / express bus |

## Configuration

### Getting an API Key

1. Go to [openpublictransport.net/api-key](https://openpublictransport.net/api-key)
2. Enter your name, email, and a brief description of your use case
3. You will receive a key by email within a few hours

### Setup Steps

1. In Home Assistant, go to **Settings → Integrations → Add Integration**
2. Search for *Public Transport Departures*
3. Select **Entry Type**: Abfahrtsanzeige / Departure Monitor
4. Select **Provider**: `Deutschland — Community Server (api.openpublictransport.net, API Key)`
5. Enter your API key
6. Search for your stop (see stop search tips below)
7. Configure departure count, transport types, and scan interval

### Stop Search Tips

The gtfs.de feed stores VRR/NRW stops with a city prefix. The integration handles this automatically — just search naturally:

| What you type | What it searches |
|---------------|-----------------|
| `Elbruchstraße` | Tries `Elbruchstraße`, then all city prefixes in parallel → finds `D-Elbruchstraße` |
| `Düsseldorf Elbruchstraße` | Detects city → searches `D-Elbruchstraße` directly |
| `Elbruchstraße, Düsseldorf` | Detects city → searches `D-Elbruchstraße` directly |
| `Hauptbahnhof` | Found directly (no prefix needed) |
| `Hamburg Hbf` | Detects no prefix needed, found directly |

!!! tip
    For NRW stops (VRR area), entering the city name together with the stop name (e.g. `Düsseldorf Hauptbahnhof`) gives the fastest result.

## Multi-Platform Stop Merging

GTFS stores one entry per platform/direction. The integration automatically groups stops by name and creates compound IDs (`gtfsde:537545|gtfsde:568685`). When fetching departures, all platforms are queried in parallel and merged — the sensor shows a complete view of the station.

## Self-Hosting

You can run your own OTP2 instance with gtfs.de data using the Docker image:

```bash
docker pull ghcr.io/nerdysoftpaw/otp-gtfsde:latest
```

See [github.com/NerdySoftPaw/otp-gtfsde](https://github.com/NerdySoftPaw/otp-gtfsde) for the full setup guide. Once running, use the **OTP2 Custom** provider instead and point it at your server.

## Realtime Data

The community server polls `realtime.gtfs.de` every 30 seconds. Coverage varies by Verbund:

| Verbund | Realtime |
|---------|----------|
| VRR (NRW) | Yes |
| BSVG (Braunschweig) | Yes |
| NWL (Westfalen-Lippe) | Yes |
| MVV (München) | Yes |
| S-Bahn Berlin | Yes |
| And more... | See [gtfs.de/de/realtime](https://gtfs.de/de/realtime/) |

!!! note
    Realtime coverage depends on the GTFS-RT feed from each Verbund. If your stop shows no delays, the Verbund may not provide a realtime feed. Scheduled times are always available.

## Troubleshooting

### HTTP 401

Your API key is invalid or not passed. Make sure you:

1. Entered the key in the integration setup step (not left blank)
2. Deleted and re-added the integration if you previously added it without a key

### No Stops Found

- Try entering the city name together with the stop: `Köln Hbf` instead of `Hbf`
- Some very small stops may not be in the GTFS feed
- Check [openpublictransport.net](https://openpublictransport.net) for server status

### No Departures

The stop exists but shows no departures:

- The stop may be a platform-only ID — try searching again to pick the compound stop
- Check if the stop has service at the current time
- Night / low-frequency service may not appear within the default time window
