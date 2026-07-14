# BART (Bay Area Rapid Transit)

BART provides departures for the San Francisco Bay Area rapid transit network via the modern HAFAS `mgate.exe` gateway.

## Coverage Area

- San Francisco Bay Area (California, USA)
- BART metro lines
- Connecting regional rail and bus where available

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://planner.bart.gov/bin/mgate.exe` |
| **API Key** | Not required (unsigned mgate) |
| **Timezone** | America/Los_Angeles |
| **Data Format** | HAFAS mgate (JSON) |

## Transport Types

| Category (catOut) | Type | Description |
|-------------------|------|-------------|
| Metro | subway | BART lines (Yellow, Red, Blue, Green, …) |
| Bus | bus | Connecting bus |
| Ferry | ferry | Connecting ferry |

## Configuration

### Setup Steps

1. Select **BART -- USA (San Francisco)** as provider
2. Search for your stop (e.g. "Powell Street")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Powell Street
- Embarcadero
- Downtown Berkeley
- San Francisco Int'l Airport (SFO)

## Features

- Realtime departure data with delay in minutes
- Platform information
- No API key required
