# PID (Pražská integrovaná doprava)

PID provides real-time departures for Prague and Central Bohemia via the Golemio open data API. A free API key is required.

## Coverage Area

- Prague metro, trams and buses
- Esko commuter trains in Prague and Central Bohemia
- Regional buses of the PID system

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://api.golemio.cz/v2/pid/departureboards` |
| **API Key** | **Required** (free) |
| **Timezone** | Europe/Prague |
| **Data Format** | Golemio REST |

## Getting an API Key

Register for free at [api.golemio.cz/api-keys](https://api.golemio.cz/api-keys) and copy the generated token.

Enter the key in the config flow when you pick the provider.

## Configuration

### Setup Steps

1. Select **PID — Tschechien (Prag, API Key)** as provider
2. Enter your API key
3. Search for your stop (e.g. "Můstek")
4. Select the stop and configure departures and filters

### Example Stops

- Můstek
- Anděl
- Hlavní nádraží
- Náměstí Míru

## Features

- Real-time departures with delay in minutes
- Platform information
- Free API key

!!! warning "New provider"
    This provider was built from the official API documentation and could not yet be tested with a real key. Please report any problems on GitHub.
