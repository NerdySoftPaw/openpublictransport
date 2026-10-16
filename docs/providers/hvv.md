# HVV (Hamburger Verkehrsverbund)

HVV is the transit authority for the Hamburg metropolitan area in Germany.

## Coverage Area

- Hamburg
- Parts of Lower Saxony
- Parts of Schleswig-Holstein

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://hvv.efa.de/efa/` |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

| Class | Type | Description |
|-------|------|-------------|
| 0 | train | High-speed trains |
| 1, 2 | subway | U-Bahn |
| 3, 4 | tram | S-Bahn |
| 5-8 | bus | Various bus types (Metrobus, Schnellbus, etc.) |
| 9 | ferry | Hafenfähre (Harbor Ferry) |

## Configuration

### Setup Steps

1. Select **HVV** as provider
2. Search for your stop (e.g., "Hamburg Hauptbahnhof")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Hamburg Hauptbahnhof
- Hamburg Altona
- Hamburg Jungfernstieg
- Hamburg Landungsbrücken

## Special Features

### Ferry Services

HVV operates harbor ferry services (Hafenfähren) that are part of the regular transit network. These are included with your HVV ticket and show up as `ferry` transport type.

### Platform Information

Platform information is extracted from `location.properties.platform` in the API response.

### Real-time Detection

HVV real-time data is detected by comparing `departureTimePlanned` with `departureTimeEstimated`.

## API Response Example

```json
{
  "stopEvents": [
    {
      "location": {
        "name": "Stadionstraße",
        "properties": {
          "stopId": "28582004",
          "platform": "1"
        }
      },
      "departureTimePlanned": "2025-06-22T20:00:00Z",
      "transportation": {
        "number": "2",
        "description": "Berliner Tor > Hbf. > Altona > Schenefeld",
        "product": {
          "class": 5,
          "name": "Bus"
        },
        "destination": {
          "name": "Schenefeld, Schenefelder Platz"
        }
      }
    }
  ]
}
```

## API URLs

### Stop Search

```
https://hvv.efa.de/efa/XML_STOPFINDER_REQUEST?outputFormat=rapidJSON&locationServerActive=1&type_sf=stop&name_sf=Hamburg%20Hauptbahnhof
```

### Departures

```
https://hvv.efa.de/efa/XML_DM_REQUEST?outputFormat=rapidJSON&stateless=1&type_dm=any&name_dm=STATION_ID&mode=direct&useRealtime=1&limit=10
```
