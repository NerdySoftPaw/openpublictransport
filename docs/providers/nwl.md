# NWL (Nahverkehr Westfalen-Lippe)

NWL is the transit authority for the Westfalen-Lippe region in North Rhine-Westphalia, Germany.

## Coverage Area

- Dortmund
- Münster
- Bielefeld
- Westfalen-Lippe region

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://westfalenfahrplan.de/nwl-efa/` |
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

1. Select **NWL** as provider
2. Search for your stop (e.g., "Hauptbahnhof")
3. Select the stop from the list
4. Configure departure count and filters

## Example Stops

- Dortmund Hauptbahnhof
- Münster Hauptbahnhof
- Bielefeld Jahnplatz
- Dortmund Kampstraße
