# SL (Storstockholms Lokaltrafik)

SL provides real-time departures for Stockholm via the official SL Transport API — no API key needed (unlike the Trafiklab provider).

## Coverage Area

- Tunnelbana (metro)
- Pendeltåg (commuter rail), Roslagsbanan, Saltsjöbanan
- Trams (Spårväg City, Tvärbanan), buses and ferries

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://transport.integration.sl.se/v1/` |
| **API Key** | Not required |
| **Timezone** | Europe/Stockholm |
| **Data Format** | SL Transport REST |

## Configuration

### Setup Steps

1. Select **SL — Schweden (Stockholm, ohne API Key)** as provider
2. Search for your stop (e.g. "T-Centralen")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- T-Centralen
- Slussen
- Odenplan
- Gamla stan

## Features

- Real-time departures with delay in minutes
- Platform information
- No API key required
