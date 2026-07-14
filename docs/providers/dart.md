# DART (Des Moines Area Rapid Transit)

DART provides departures for the Des Moines, Iowa (USA) transit network via the modern HAFAS `mgate.exe` gateway.

!!! note
    The upstream endpoint (`dart.hafas.de`) is catalogued by public-transport/transport-apis as "Dallas Area Rapid Transit", but it actually serves **Des Moines, Iowa** (DART Central Station; Des Moines / West Des Moines / Ankeny / Johnston stops) — verified live.

## Coverage Area

- Greater Des Moines, Iowa (USA)
- DART bus network (local, express, on-call)

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://dart.hafas.de/bin/mgate.exe` |
| **API Key** | Not required (unsigned mgate) |
| **Timezone** | America/Chicago |
| **Data Format** | HAFAS mgate (JSON) |

## Transport Types

| Category (catOut) | Type | Description |
|-------------------|------|-------------|
| Bus | bus | DART bus routes |

## Configuration

### Setup Steps

1. Select **DART -- USA (Des Moines)** as provider
2. Search for your stop (e.g. "DART Central Station")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- DART Central Station
- Merle Hay Rd / Urbandale Ave
- SE 14th St / Southdale Shopping Center

## Features

- Realtime departure data with delay in minutes
- No API key required
