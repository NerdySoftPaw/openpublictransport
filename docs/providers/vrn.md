# VRN (Verkehrsverbund Rhein-Neckar)

VRN is the transit authority for the Rhein-Neckar metropolitan area in Germany.

## Coverage Area

- Mannheim
- Heidelberg
- Ludwigshafen
- Rhein-Neckar region

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://www.vrn.de/mngvrn/` |
| **API Type** | EFA |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

VRN uses the standard EFA transport class mapping:

| Class | Type | Description |
|-------|------|-------------|
| 0, 1 | train | Trains (ICE, IC, RE, RB) |
| 2, 3 | subway | U-Bahn |
| 4 | tram | Tram |
| 5-8, 11 | bus | Bus services |
| 9 | ferry | Ferry |
| 10 | taxi | Taxi |
| 13 | train | Regional (RE) |
| 15 | train | InterCity (IC) |
| 16 | train | ICE |

## Setup Steps

1. Select **VRN** as provider
2. Search for your stop (e.g., "Paradeplatz")
3. Select the stop from the list
4. Configure departure count and filters

## Example Stops

- Mannheim Hauptbahnhof
- Heidelberg Bismarckplatz
- Mannheim Paradeplatz
- Heidelberg Hauptbahnhof
