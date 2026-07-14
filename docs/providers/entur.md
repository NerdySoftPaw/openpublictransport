# Entur (Norway)

Entur is Norway's national journey planner, aggregating every Norwegian public transport operator. Departures come from Entur's OTP **transmodel** GraphQL API and stop search from Entur's geocoder.

## Coverage Area

- All of Norway
- National and regional rail (Vy, SJ, Go-Ahead, …)
- Regional bus, tram, metro (T-bane) and ferry operators (Ruter, Skyss, AtB, …)

## API Details

| Property | Value |
|----------|-------|
| **Geocoder** | `https://api.entur.io/geocoder/v1/autocomplete` |
| **Journey planner** | `https://api.entur.io/journey-planner/v3/graphql` |
| **API Key** | Not required (sends an `ET-Client-Name` header) |
| **Timezone** | Europe/Oslo |
| **Data Format** | OTP transmodel GraphQL |

## Transport Types

| transportMode | Type | Description |
|---------------|------|-------------|
| rail | train | National / regional trains |
| metro | subway | Oslo T-bane |
| tram | tram | Tram / trikk |
| bus | bus | City and regional bus |
| coach | bus | Express coach |
| water | ferry | Ferry / boat |

## Configuration

### Setup Steps

1. Select **Entur -- Norwegen** as provider
2. Search for your stop (e.g. "Oslo S")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Oslo S
- Bergen stasjon
- Trondheim S
- Stavanger stasjon

## Features

- Realtime departure data with delay in minutes
- Cancellation flag surfaced as a notice
- Platform / quay information
- No API key required
