# GVH (Großraum-Verkehr Hannover)

GVH provides departures for Hannover, Germany via the EFA journey planner.

## Coverage Area

- Region Hannover (ÜSTRA Stadtbahn and bus, regiobus)
- S-Bahn Hannover and regional trains
- The server also finds stops elsewhere in Lower Saxony, but real-time data is best inside the GVH area

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://www.efa.de/efa/` |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |
| **Data Format** | EFA rapidJSON |

## Transport Types

| EFA class | Type | Description |
|-----------|------|-------------|
| 0, 1, 13–16, 18 | train | Long-distance, regional and S-Bahn trains |
| 2 | subway | U-Bahn |
| 3, 4, 8 | tram | Stadtbahn, tram, cable / rack railway |
| 5, 6, 7, 10, 11, 17, 19 | bus | City, regional and express buses, on-demand, rail replacement, Bürgerbus |
| 9 | ferry | Ferries |

## Configuration

### Setup Steps

1. Select **GVH — Hannover** as provider
2. Search for your stop (e.g. "Hannover, Kröpcke/Theaterstraße")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Hannover, Kröpcke/Theaterstraße
- Hannover, Hauptbahnhof
- Hannover, Aegidientorplatz
- Langenhagen, Zentrum

## Features

- Real-time departures with delay in minutes
- Platform information
- No API key required
- Trip planning
