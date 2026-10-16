# KVV (Karlsruher Verkehrsverbund)

KVV is the transit authority for the Karlsruhe region in Baden-Württemberg, Germany.

## Coverage Area

- Karlsruhe
- Rastatt
- Ettlingen
- Bruchsal
- And surrounding areas

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://projekte.kvv-efa.de/sl3-alone/` |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

KVV uses the same transport class mapping as VRR:

| Class | Type | Description |
|-------|------|-------------|
| 0, 1 | train | Trains |
| 2, 3 | subway | Stadtbahn |
| 4 | tram | Tram |
| 5-8, 11 | bus | Bus services |
| 9 | ferry | Ferry |

## Configuration

### Setup Steps

1. Select **KVV** as provider
2. Search for your stop (e.g., "Karlsruhe Hauptbahnhof")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Karlsruhe Hauptbahnhof
- Karlsruhe Marktplatz
- Karlsruhe Durlacher Tor
- Ettlingen Stadt

## Special Features

### Tram-Train System

KVV operates a unique tram-train system where light rail vehicles can travel on both city tram lines and regional rail tracks. This means:

- S-Bahn lines operate as tram in the city center
- Same vehicle type serves urban and suburban areas

### Platform Information

Platform information is extracted from the `location.disassembledName` field in the API response.

## API URLs

### Stop Search

```
https://projekte.kvv-efa.de/sl3-alone/XML_STOPFINDER_REQUEST?outputFormat=rapidJSON&locationServerActive=1&type_sf=stop&name_sf=Karlsruhe%20Hauptbahnhof
```

### Departures

```
https://projekte.kvv-efa.de/sl3-alone/XML_DM_REQUEST?outputFormat=rapidJSON&stateless=1&type_dm=any&name_dm=STATION_ID&mode=direct&useRealtime=1&limit=10
```
