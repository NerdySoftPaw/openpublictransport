# TPG (Transports publics genevois)

TPG provides departures for Geneva, Switzerland via the modern HAFAS `mgate.exe` gateway.

## Coverage Area

- Canton of Geneva (Switzerland) and surroundings
- TPG tram and bus
- Regional trains calling in the Geneva area (incl. cross-border TER to France)

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://tpg.hafas.cloud/bin/mgate.exe` |
| **API Key** | Not required (unsigned mgate) |
| **Timezone** | Europe/Zurich |
| **Data Format** | HAFAS mgate (JSON) |

## Transport Types

| Category (catOut) | Type | Description |
|-------------------|------|-------------|
| Tram | tram | TPG tram lines |
| B (Bus) | bus | TPG bus lines |
| TER / Train | train | Regional / cross-border trains |

## Configuration

### Setup Steps

1. Select **TPG -- Schweiz (Genf)** as provider
2. Search for your stop (e.g. "Genève, Cornavin")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Genève, Cornavin
- Genève-Aéroport
- Genève, Rive
- Genève, Bel-Air

## Features

- Realtime departure data with delay in minutes
- Platform information
- No API key required
