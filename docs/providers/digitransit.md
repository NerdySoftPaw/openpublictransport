# Digitransit (Finland)

Digitransit provides real-time departures for all of Finland (HSL Helsinki, Waltti cities and national rail) via its OpenTripPlanner 2 API. A free subscription key is required.

## Coverage Area

- HSL (Helsinki region): metro, trams, buses, commuter trains, ferries
- Waltti cities (Tampere, Turku, Oulu, Jyväskylä, …)
- VR long-distance and regional trains

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://api.digitransit.fi/routing/v2/finland/gtfs/v1` |
| **API Key** | **Required** (free) |
| **Timezone** | Europe/Helsinki |
| **Data Format** | OTP2 GraphQL |

## Getting an API Key

Register for free at [portal-api.digitransit.fi](https://portal-api.digitransit.fi/) and subscribe to the routing API.

Enter the key in the config flow when you pick the provider.

## Configuration

### Setup Steps

1. Select **Digitransit — Finnland (API Key)** as provider
2. Enter your API key
3. Search for your stop (e.g. "Rautatientori")
4. Select the stop and configure departures and filters

### Example Stops

- Rautatientori
- Kamppi
- Pasila
- Tampere asema

## Features

- Real-time departures with delay in minutes
- Platform information
- Free API key

!!! warning "New provider"
    This provider was built from the official API documentation and could not yet be tested with a real key. Please report any problems on GitHub.
