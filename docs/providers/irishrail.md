# Iarnród Éireann (Irish Rail)

Iarnród Éireann / Irish Rail provides departures for Ireland's national rail network via the modern HAFAS `mgate.exe` gateway.

## Coverage Area

- All of Ireland
- InterCity, Commuter and DART rail
- Luas (Dublin tram) where available

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://journeyplanner.irishrail.ie/bin/mgate.exe` |
| **API Key** | Not required (unsigned mgate) |
| **Timezone** | Europe/Dublin |
| **Data Format** | HAFAS mgate (JSON) |

## Transport Types

| Category (catOut) | Type | Description |
|-------------------|------|-------------|
| InterCity | train | InterCity rail |
| Commuter / Train | train | Commuter rail |
| DART | train | Dublin Area Rapid Transit (electric rail) |
| Luas | tram | Dublin tram |

## Configuration

### Setup Steps

1. Select **Irish Rail -- Irland** as provider
2. Search for your stop (e.g. "Dublin Connolly")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Dublin Connolly
- Dublin Heuston
- Cork Kent
- Galway Ceannt

## Features

- Realtime departure data with delay in minutes
- Platform information
- No API key required
