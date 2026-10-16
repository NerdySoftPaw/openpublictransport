# Transport for NSW

Transport for NSW provides real-time departures for New South Wales via the official Trip Planner API (EFA). A free API key is required.

## Coverage Area

- Sydney Trains and NSW TrainLink
- Sydney Metro and Light Rail
- Buses and ferries across NSW

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://api.transport.nsw.gov.au/v1/tp/` |
| **API Key** | **Required** (free) |
| **Timezone** | Australia/Sydney |
| **Data Format** | EFA (TfNSW Trip Planner API) |

## Getting an API Key

Register for free at [opendata.transport.nsw.gov.au](https://opendata.transport.nsw.gov.au/) and create an API key for the Trip Planner APIs.

Enter the key in the config flow when you pick the provider.

## Configuration

### Setup Steps

1. Select **TfNSW — Australien (Sydney / NSW, API Key)** as provider
2. Enter your API key
3. Search for your stop (e.g. "Central Station")
4. Select the stop and configure departures and filters

### Example Stops

- Central Station
- Town Hall Station
- Circular Quay
- Parramatta Station

## Features

- Real-time departures with delay in minutes
- Platform information
- Free API key

!!! warning "New provider"
    This provider was built from the official API documentation and could not yet be tested with a real key. Please report any problems on GitHub.
