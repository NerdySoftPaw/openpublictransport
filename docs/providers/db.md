# DB (Deutsche Bahn)

Nationwide departures for Germany, from long-distance ICE services down to local
buses, served through [Transitous](transitous.md) (MOTIS 2), which carries the
nationwide DELFI timetable together with DB real-time data.

!!! info "New backend since v2026.10.0"
    The provider used to query the community proxy `v6.db.transport.rest`, which has
    been unavailable since autumn 2026. Existing DB entries keep working: their old
    station numbers are matched to the Transitous stop by name on the first update.

## Coverage Area

- All DB long-distance services (ICE, IC, EC)
- Regional and suburban rail nationwide (RE, RB, S-Bahn)
- Local transport wherever the underlying HAFAS data carries it (U-Bahn, tram, bus, ferry)

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://api.transitous.org/api` |
| **API Type** | MOTIS 2 REST |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

Transitous reports GTFS route types; the mapping is the same as for the
[Transitous](transitous.md) provider:

| Transitous mode | Type | Description |
|-----------------|------|-------------|
| HIGHSPEED_RAIL / LONG_DISTANCE / NIGHT_RAIL | train | ICE, IC / EC, night trains |
| REGIONAL_FAST_RAIL / REGIONAL_RAIL / SUBURBAN | train | RE, RB, S-Bahn |
| SUBWAY | subway | U-Bahn |
| TRAM | tram | Tram / Straßenbahn |
| BUS / COACH / ODM | bus | Bus, long-distance coach, on-demand |
| FERRY | ferry | Ferry |

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

Cancellations and service notes from the real-time feed appear in the departure
attributes.

## Limitations

- Trip planning is not available for this provider; use an EFA provider or
  a self-hosted [OTP2 Custom](otp-custom.md) instance for A-to-B routing.
- Transitous is a community service with a fair-use policy. The integration's default
  scan interval of 60 seconds is well within it.
