# DB (Deutsche Bahn)

Nationwide departures for Germany, from long-distance ICE services down to local
buses, through the community-run `v6.db.transport.rest` API.

!!! note "Community proxy, not an official DB service"
    `v6.db.transport.rest` is maintained by [derhuerst](https://github.com/derhuerst)
    and is free and open, but it is not operated or supported by Deutsche Bahn.
    Availability is not guaranteed — occasional downtime is normal. For a
    nationwide provider with an availability promise, use
    [openpublictransport](openpublictransport.md).

## Coverage Area

- All DB long-distance services (ICE, IC, EC)
- Regional and suburban rail nationwide (RE, RB, S-Bahn)
- Local transport wherever the underlying HAFAS data carries it (U-Bahn, tram, bus, ferry)

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://v6.db.transport.rest` |
| **API Type** | FPTF REST |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

DB uses FPTF (Friendly Public Transport Format) product types:

| Product | Type | Description |
|---------|------|-------------|
| nationalExpress | train | ICE |
| national | train | IC / EC |
| regionalExpress | train | RE |
| regional | train | RB |
| suburban | train | S-Bahn |
| subway | subway | U-Bahn |
| tram | tram | Tram / Straßenbahn |
| bus | bus | Bus services |
| ferry | ferry | Ferry |
| taxi | taxi | Rufbus / Anruf-Sammeltaxi |

## Configuration

### Setup Steps

1. Select **DB** as provider
2. Search for your stop (e.g., "Köln Hbf")
3. Select the stop from the list
4. Choose transport types and the number of departures

### Example Stops

- `Berlin Hbf`
- `München Hbf`
- `Hamburg Dammtor`
- `Köln Messe/Deutz`

## Special Features

### Real-Time Data

Departures carry the planned time plus the live estimate, so delays and platform
changes come through the same as on the regional providers.

### Notices

Service messages are read from the FPTF `remarks` list — disruptions, cancellations
and operator notes appear in the departure attributes.

## Limitations

- Trip planning is not available for this provider; use an EFA provider or
  [openpublictransport](openpublictransport.md) for A-to-B routing.
- The proxy applies its own rate limits. The integration's default scan interval of
  60 seconds is well within them.
