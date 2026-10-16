# TfL (Transport for London)

TfL provides real-time arrivals for London via the TfL Unified API. It works without a key; an optional free app key raises the rate limit.

## Coverage Area

- London Underground
- London buses
- DLR, London Overground, Elizabeth line, Trams

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://api.tfl.gov.uk/` |
| **API Key** | Optional (free app key raises the rate limit) |
| **Timezone** | Europe/London |
| **Data Format** | TfL Unified API |

## Configuration

### Setup Steps

1. Select **TfL — Großbritannien (London)** as provider
2. Search for your stop (e.g. "Oxford Circus Underground Station")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Oxford Circus Underground Station
- King's Cross & St Pancras International
- Waterloo
- Canary Wharf

## Features

- Real-time departures (predictions)
- Platform information
- Works without an API key

!!! note
    TfL predicts arrivals only, so there is no scheduled time or delay. Stations with many stops (hubs like King's Cross) query every child stop.
