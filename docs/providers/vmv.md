# VMV (Verkehrsgesellschaft Mecklenburg-Vorpommern)

VMV provides departures for Mecklenburg-Vorpommern, Germany via the EFA journey planner.

## Coverage Area

- All of Mecklenburg-Vorpommern
- Rostock (RSAG tram and bus), Schwerin, Greifswald, Stralsund, Neubrandenburg, Wismar
- Regional trains and buses across the state

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://fahrplanauskunft-mv.de/vmv-efa/` |
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

1. Select **VMV — Mecklenburg-Vorpommern** as provider
2. Search for your stop (e.g. "Rostock, Hauptbahnhof")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Rostock, Hauptbahnhof
- Schwerin, Marienplatz
- Greifswald, Bahnhof
- Stralsund, Hauptbahnhof

## Features

- Real-time departures with delay in minutes
- Platform information
- No API key required
- Trip planning

!!! note
    Stop search on this server is slow (around 3–4 seconds). Departure updates are fast.
