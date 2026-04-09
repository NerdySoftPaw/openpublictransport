# VGN (Verkehrsverbund Großraum Nürnberg)

!!! warning "Temporarily Disabled"
    The VGN provider is currently disabled due to API compatibility issues. The code is still in the repository and will be re-enabled once the issues are resolved.

VGN is the transit authority for the Nuremberg greater area in Bavaria, Germany.

## Coverage Area

- Nuremberg (Nürnberg)
- Fürth
- Erlangen
- Bamberg
- And surrounding areas

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://efa.vgn.de/vgnExt_oeffi/` |
| **API Type** | EFA |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

VGN uses the same EFA transport class mapping as VRR/KVV:

| Class | Type | Description |
|-------|------|-------------|
| 0, 1 | train | Trains (Regionalzug) |
| 2, 3 | subway | U-Bahn / S-Bahn |
| 4 | tram | Tram |
| 5-8, 11 | bus | Bus services |
| 9 | ferry | Ferry |
| 13 | train | Regional (RE) |
| 15 | train | InterCity (IC) |
| 16 | train | ICE |

## Configuration

### Setup Steps

1. Select **VGN** as provider
2. Search for your stop (e.g., "Hauptbahnhof")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Hauptbahnhof
- Plärrer
- Lorenzkirche
- Rathenauplatz

## Special Features

### Nuremberg Metro

Nuremberg operates a U-Bahn system with both conventional and fully automated driverless trains (Line U3), making it one of the most modern metro systems in Germany.

### S-Bahn Nürnberg

The S-Bahn network connects Nuremberg with surrounding cities including Fürth, Erlangen, and Bamberg.

### Tram Network

Nuremberg's tram network provides inner-city connections alongside the U-Bahn system.

### Platform Information

Platform information is extracted from the `location.disassembledName` field in the EFA API response.

## API URLs

### Stop Search

```
https://efa.vgn.de/vgnExt_oeffi/XML_STOPFINDER_REQUEST?outputFormat=RapidJSON&locationServerActive=1&type_sf=stop&name_sf=Hauptbahnhof
```

### Departures

```
https://efa.vgn.de/vgnExt_oeffi/XML_DM_REQUEST?outputFormat=RapidJSON&stateless=1&type_dm=any&name_dm=STATION_ID&mode=direct&useRealtime=1&limit=10
```
