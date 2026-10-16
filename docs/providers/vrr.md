# VRR (Verkehrsverbund Rhein-Ruhr)

VRR is the transit authority for the Rhein-Ruhr metropolitan area in North Rhine-Westphalia, Germany.

## Coverage Area

- Düsseldorf
- Essen
- Dortmund
- Duisburg
- Bochum
- Wuppertal
- And surrounding areas

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://openservice.vrr.de/static03/` |
| **API Key** | Not required |
| **Rate Limit** | 60,000 calls/day |
| **Timezone** | Europe/Berlin |

## Transport Types

| Class | Type | Description |
|-------|------|-------------|
| 0, 1 | train | Legacy trains |
| 2, 3 | subway | U-Bahn |
| 4 | tram | Tram |
| 5-8, 11 | bus | Various bus types |
| 9 | ferry | Ferry |
| 10 | taxi | Taxi |
| 13 | train | Regional (RE) |
| 15 | train | InterCity (IC) |
| 16 | train | ICE |

## Configuration

### Setup Steps

1. Select **VRR** as provider
2. Search for your stop (e.g., "Düsseldorf Hauptbahnhof")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Düsseldorf Hauptbahnhof
- Essen Hauptbahnhof
- Dortmund Hauptbahnhof
- Duisburg Hauptbahnhof

## API URLs

### Stop Search (STOPFINDER)

```
https://openservice.vrr.de/static03/XML_STOPFINDER_REQUEST?outputFormat=rapidJSON&locationServerActive=1&type_sf=stop&name_sf=Düsseldorf%20Hauptbahnhof
```

### Departures (DM_REQUEST)

Using Station ID:
```
https://openservice.vrr.de/static03/XML_DM_REQUEST?outputFormat=rapidJSON&stateless=1&type_dm=any&name_dm=20018235&mode=direct&useRealtime=1&limit=10
```

Using Place and Name:
```
https://openservice.vrr.de/static03/XML_DM_REQUEST?outputFormat=rapidJSON&place_dm=Düsseldorf&type_dm=stop&name_dm=Hauptbahnhof&mode=direct&useRealtime=1&limit=10
```

## Features

- Full real-time departure data
- Delay information in minutes
- Platform/track information
- All major transport types supported
- Fuzzy search with typo tolerance
