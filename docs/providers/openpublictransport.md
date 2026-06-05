# openpublictransport (Deutschland, Community Server)

!!! info "Community Server"
    This provider uses a community-hosted OTP2 server at **api.openpublictransport.net**, backed by [gtfs.de](https://gtfs.de) data (CC 4.0, Germany-wide). An API key is required — [request one here](https://openpublictransport.net/api-key).

    The `openpublictransport` provider gives you Germany-wide real-time departures for all transit modes — S-Bahn, U-Bahn, Bus, Tram, Regional, IC/ICE — from a single unified endpoint. Static GTFS data is rebuilt weekly (every Sunday night) from gtfs.de and enriched with GTFS-RT realtime delays every 30 seconds from VBB, VRR, VRS, VRN, VVO, VBN, NVBW, DEFAS Bayern, VAG Nürnberg, Stadtwerke Münster, and more.

## Coverage Area

- All of Germany (461 agencies, 437 000+ stops)
- Data source: [gtfs.de](https://gtfs.de) Germany Full feed (CC 4.0)
- Realtime: [realtime.gtfs.de](https://gtfs.de/de/realtime/) GTFS-RT (VRR, BSVG, NWL, MVV, S-Bahn Berlin, and more)

## API Details

| Property | Value |
|----------|-------|
| **Server** | `https://api.openpublictransport.net/otp/routers/default` |
| **GraphQL Endpoint** | `https://api.openpublictransport.net/otp/gtfs/v1` |
| **API Type** | OTP2 GraphQL |
| **API Key** | Yes — [request free key](https://openpublictransport.net/api-key) |
| **Timezone** | Europe/Berlin |
| **Data Source** | gtfs.de CC 4.0 + GTFS-RT |
| **GTFS Refresh** | Weekly (Sunday ~2:00 AM) + Realtime every 30s |
| **Maintenance** | Every Sunday ~2:00–3:30 AM Europe/Berlin (~80 min offline) |

## Scheduled Maintenance

The community server rebuilds its routing graph every **Sunday at approximately 2:00 AM (Europe/Berlin)**. During this window (roughly 80 minutes), the API is completely offline.

| | |
|---|---|
| **Schedule** | Every Sunday, ~2:00 AM Europe/Berlin |
| **Duration** | ~80 minutes (graph rebuild ~57 min + loading ~20 min) |
| **Impact** | API unreachable; sensors show connection errors |
| **After rebuild** | Fresh weekly GTFS data, realtime resumes within seconds |

!!! tip
    If you have Home Assistant automations that run on Sunday mornings, schedule them after **4:00 AM** to ensure the API is back online.

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

## Lovelace Card

The [openpublictransport-card](https://github.com/NerdySoftPaw/openpublictransport-card) provides four layouts for visualizing departure data:

| Layout | Best for |
|--------|----------|
| `table` | Classic departure board — all departures at a glance |
| `compact` | Space-efficient chip view for dense dashboards |
| `next` | Single large "next departure" widget for quick glance |
| `trip` | Multi-leg A→B journey planning display |

**Line badge colors** are applied automatically — the openpublictransport provider returns `line_color` and `line_text_color` for many lines (e.g., VBB Berlin, where U-Bahn lines show their official colors).

**Card-side line filter** — the card's `line_filter` option lets you show only specific lines per card instance, independently of the integration's own line filter:

```yaml
type: custom:openpublictransport-card
entity: sensor.dusseldorf_hbf_departures
layout: table
line_filter: "U79, U75"   # show only U79 and U75 in this card
```

!!! tip
    The **integration's** `line_filter` (set during HA config) reduces API load for all entities from that stop. The **card's** `line_filter` is purely visual — use it to show different subsets of the same sensor in multiple cards.

## Self-Hosting

You can run your own OTP2 instance with gtfs.de data using the Docker image:

```bash
docker pull ghcr.io/nerdysoftpaw/otp-gtfsde:latest
```

See [github.com/NerdySoftPaw/otp-gtfsde](https://github.com/NerdySoftPaw/otp-gtfsde) for the full setup guide. Once running, use the **OTP2 Custom** provider instead and point it at your server.

## Realtime Data

The community server polls `realtime.gtfs.de/realtime-free.pb` every 30 seconds (update frequency on the source side: every 10 s). This single aggregated feed combines data from the following regional providers:

| Verbund / Provider | Region | Modes |
|--------------------|--------|-------|
| VBB | Berlin & Brandenburg | All modes |
| VRR | Rhein-Ruhr (NRW) | All modes (bus partially) |
| VRS | Rhein-Sieg (Köln/Bonn) | All modes |
| VRN / RNN | Rhein-Neckar | Local transit |
| VVO | Dresden & Chemnitz (Oberelbe) | All modes |
| VBN | Bremen, Niedersachsen, Schleswig-Holstein | All modes |
| NVBW | Baden-Württemberg | All modes (bus partially) |
| DEFAS Bayern | Bavaria (incl. MVV, S-Bahn München) | All modes |
| VAG Nürnberg | Nürnberg city | Urban transit |
| Stadtwerke Münster | Münster city | Local transit |
| opentransportdata.swiss | Baden-Württemberg / Swiss border | Cross-border |
| OVapi | Netherlands / German border | Cross-border |
| DELFI SIRI feeds | Various states | Multiple regions |

!!! note
    Realtime coverage depends on what each Verbund contributes to the feed. If your stop shows no delays, the operator may not yet provide GTFS-RT data. Scheduled departure times are always available regardless of realtime coverage.
    
    See [gtfs.de/de/realtime](https://gtfs.de/de/realtime/) for the full feed list and licensing details.

## Troubleshooting

### API Offline on Sunday Morning

If all sensors fail with connection errors on Sunday between 2:00–4:00 AM (Europe/Berlin), this is the scheduled weekly maintenance window. No action needed — the API recovers automatically after ~80 minutes.

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
