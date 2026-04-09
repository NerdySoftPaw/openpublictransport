# MVV (Münchner Verkehrs- und Tarifverbund)

MVV is the transit authority for the Munich metropolitan area in Bavaria, Germany.

## Coverage Area

- Munich (München)
- Surrounding counties (Landkreise)
- Munich metropolitan area

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://efa.mvv-muenchen.de/ng/` |
| **API Type** | EFA |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

MVV uses the same EFA transport class mapping as VRR/KVV:

| Class | Type | Description |
|-------|------|-------------|
| 0, 1 | train | Trains (Regionalzug) |
| 2, 3 | subway | U-Bahn |
| 4 | tram | Tram |
| 5-8, 11 | bus | Bus services |
| 9 | ferry | Ferry |
| 13 | train | Regional (RE) |
| 15 | train | InterCity (IC) |
| 16 | train | ICE |

## Configuration

### Setup Steps

1. Select **MVV** as provider
2. Search for your stop (e.g., "Marienplatz")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Marienplatz
- Hauptbahnhof
- Ostbahnhof
- Münchner Freiheit

## Special Features

### Munich Transit Network

MVV covers one of Germany's largest transit networks, including:

- **S-Bahn**: 8 suburban rail lines serving the greater Munich area
- **U-Bahn**: 8 underground lines within the city
- **Tram**: Historic and modern tram lines
- **Bus**: City and regional bus services
- **Regionalzug**: Regional train connections

### Platform Information

Platform information is extracted from the `location.disassembledName` field in the EFA API response.

## API URLs

### Stop Search

```
https://efa.mvv-muenchen.de/ng/XML_STOPFINDER_REQUEST?outputFormat=RapidJSON&locationServerActive=1&type_sf=stop&name_sf=Marienplatz
```

### Departures

```
https://efa.mvv-muenchen.de/ng/XML_DM_REQUEST?outputFormat=RapidJSON&stateless=1&type_dm=any&name_dm=STATION_ID&mode=direct&useRealtime=1&limit=10
```
