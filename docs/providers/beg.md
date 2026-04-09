# BEG (Bayerische Eisenbahngesellschaft)

BEG provides statewide transit data for Bavaria (Bayern), Germany.

## Coverage Area

- All of Bavaria
- Munich, Nuremberg, Augsburg, Regensburg, and more

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://bahnland-bayern.de/efa/` |
| **API Type** | EFA |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

| Class | Type | Description |
|-------|------|-------------|
| 0 | train | High-speed trains (ICE, IC, EC) |
| 1 | train | Regional trains (RE, RB) |
| 2, 3 | subway | U-Bahn |
| 4 | tram | Tram |
| 5-8 | bus | Bus services |
| 13 | train | Regional (RE) |

## Setup Steps

1. Select **BEG** as provider
2. Search for your stop (e.g., "München Hauptbahnhof")
3. Select the stop from the list
4. Configure departure count and filters

## Example Stops

- München Hauptbahnhof
- Nürnberg Hauptbahnhof
- Augsburg Hauptbahnhof
- Regensburg Hauptbahnhof
