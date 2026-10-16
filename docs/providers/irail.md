# iRail (SNCB / NMBS, Belgium)

iRail provides real-time departures for all Belgian railway stations (SNCB / NMBS) via the open iRail API.

## Coverage Area

- All SNCB / NMBS stations in Belgium
- IC, L, P, S trains
- Cross-border trains calling in Belgium

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://api.irail.be/v1/` |
| **API Key** | Not required |
| **Timezone** | Europe/Brussels |
| **Data Format** | iRail REST |

## Configuration

### Setup Steps

1. Select **iRail — Belgien (SNCB / NMBS)** as provider
2. Search for your stop (e.g. "Brussels-Central")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Brussels-Central
- Gent-Sint-Pieters
- Antwerpen-Centraal
- Liège-Guillemins

## Features

- Real-time departures with delay in minutes
- Platform information
- No API key required

!!! note
    iRail asks clients to stay below 3 requests per second; the default scan interval is far below that.
