# NVBW (Nahverkehrsgesellschaft Baden-Württemberg)

NVBW provides statewide transit data for Baden-Württemberg, Germany.

## Coverage Area

- All of Baden-Württemberg
- Stuttgart, Karlsruhe, Freiburg, Mannheim, Heidelberg, Ulm, and more

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://www.efa-bw.de/nvbw/` |
| **API Type** | EFA |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

| Class | Type | Description |
|-------|------|-------------|
| 0 | train | High-speed trains (ICE, IC, EC) |
| 1 | train | Regional trains (RE, RB) |
| 4 | tram | Tram |
| 5-8 | bus | Bus services |
| 13 | train | Regional (RE) |

## Setup Steps

1. Select **NVBW** as provider
2. Search for your stop (e.g., "Stuttgart Hauptbahnhof")
3. Select the stop from the list
4. Configure departure count and filters

## Example Stops

- Stuttgart Hauptbahnhof
- Karlsruhe Marktplatz
- Freiburg Bertoldsbrunnen
- Heidelberg Bismarckplatz
