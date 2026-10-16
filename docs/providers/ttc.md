# TTC (Toronto Transit Commission)

TTC provides real-time predictions for Toronto streetcars and buses via the NextBus (umo IQ) public feed.

## Coverage Area

- All TTC streetcar routes
- All TTC bus routes
- **Not included:** subway (not in the NextBus feed)

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://retro.umoiq.com/service/publicJSONFeed` |
| **API Key** | Not required |
| **Timezone** | America/Toronto |
| **Data Format** | NextBus (umo IQ) |

## Configuration

### Setup Steps

1. Select **TTC — Kanada (Toronto)** as provider
2. Search for your stop (e.g. "King St West At Spadina Ave East Side")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- King St West At Spadina Ave East Side
- Spadina Ave At King St West
- Dundas St West At Bathurst St
- Queen St West At Yonge St

## Features

- Real-time departures (predictions)
- No API key required

!!! note
    NextBus has no stop search, so the first search builds a stop index from every route (about 200 requests, roughly 12 seconds). Later searches are instant. Predictions are estimates, so there is no scheduled time or delay.
