# VVS (Verkehrs- und Tarifverbund Stuttgart)

VVS is the transit authority for the Stuttgart area in Baden-Württemberg, Germany.

## Coverage Area

- Stuttgart
- Esslingen
- Böblingen
- Ludwigsburg
- Rems-Murr-Kreis
- And surrounding areas

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://www3.vvs.de/mngvvs/` |
| **API Type** | EFA |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

VVS uses the same EFA transport class mapping as VRR/KVV:

| Class | Type | Description |
|-------|------|-------------|
| 0, 1 | train | Trains (Regionalzug) |
| 2, 3 | subway | S-Bahn / Stadtbahn |
| 4 | tram | Tram |
| 5-8, 11 | bus | Bus services |
| 13 | train | Regional (RE) |
| 15 | train | InterCity (IC) |
| 16 | train | ICE |

## Configuration

### Setup Steps

1. Select **VVS** as provider
2. Search for your stop (e.g., "Hauptbahnhof")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Hauptbahnhof
- Charlottenplatz
- Schlossplatz
- Rotebühlplatz

## Special Features

### Stadtbahn Network

Stuttgart operates an extensive Stadtbahn (light rail) network that functions similarly to a subway in the city center (underground) and as a tram in suburban areas. These are classified under transport class 2/3 in the EFA system.

### S-Bahn Stuttgart

The S-Bahn network connects Stuttgart with the surrounding region, providing rapid transit across the metropolitan area.

### Platform Information

Platform information is extracted from the `location.disassembledName` field in the EFA API response.

## API URLs

### Stop Search

```
https://www3.vvs.de/mngvvs/XML_STOPFINDER_REQUEST?outputFormat=RapidJSON&locationServerActive=1&type_sf=stop&name_sf=Hauptbahnhof
```

### Departures

```
https://www3.vvs.de/mngvvs/XML_DM_REQUEST?outputFormat=RapidJSON&stateless=1&type_dm=any&name_dm=STATION_ID&mode=direct&useRealtime=1&limit=10
```
