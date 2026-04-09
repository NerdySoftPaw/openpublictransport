# VVO (Verkehrsverbund Oberelbe)

VVO is the transit authority for the Oberelbe / Dresden region in Saxony, Germany.

## Coverage Area

- Dresden
- Meißen
- Pirna
- Oberelbe region

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://efa.vvo-online.de/VMSSL3/` |
| **API Type** | EFA |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

| Class | Type | Description |
|-------|------|-------------|
| 0 | train | High-speed trains (ICE, IC, EC) |
| 1 | train | Regional trains (RE, RB, S-Bahn) |
| 4 | tram | Tram |
| 5-8 | bus | Bus services |
| 9 | ferry | Ferry |
| 13 | train | Regional (RE) |

## Setup Steps

1. Select **VVO** as provider
2. Search for your stop (e.g., "Postplatz")
3. Select the stop from the list
4. Configure departure count and filters

## Example Stops

- Dresden Hauptbahnhof
- Dresden Postplatz
- Dresden Albertplatz
- Dresden Neustadt
