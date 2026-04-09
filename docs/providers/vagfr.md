# VAG (Freiburger Verkehrs AG)

VAG is the public transport operator for Freiburg im Breisgau in Baden-Württemberg, Germany.

## Coverage Area

- Freiburg im Breisgau
- Surrounding communities

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://efa.vagfr.de/vagfr3/` |
| **API Type** | EFA |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

VAG uses the same EFA transport class mapping as VRR/KVV:

| Class | Type | Description |
|-------|------|-------------|
| 0, 1 | train | Trains (Regionalzug) |
| 4 | tram | Tram (Straßenbahn) |
| 5-8, 11 | bus | Bus services |
| 13 | train | Regional (RE) |
| 15 | train | InterCity (IC) |
| 16 | train | ICE |

## Configuration

### Setup Steps

1. Select **VAG Freiburg** as provider
2. Search for your stop (e.g., "Hauptbahnhof")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Hauptbahnhof
- Bertoldsbrunnen
- Stadttheater
- Europaplatz

## Special Features

### Freiburg Tram Network

Freiburg operates an extensive tram network that serves as the backbone of the city's public transport. The tram lines connect major destinations throughout the city center and surrounding neighborhoods.

### Regional Connections

Through the EFA API, regional train connections (RE, RB) passing through Freiburg are also available, providing departure information for longer-distance travel.

### Platform Information

Platform information is extracted from the `location.disassembledName` field in the EFA API response.

## API URLs

### Stop Search

```
https://efa.vagfr.de/vagfr3/XML_STOPFINDER_REQUEST?outputFormat=RapidJSON&locationServerActive=1&type_sf=stop&name_sf=Hauptbahnhof
```

### Departures

```
https://efa.vagfr.de/vagfr3/XML_DM_REQUEST?outputFormat=RapidJSON&stateless=1&type_dm=any&name_dm=STATION_ID&mode=direct&useRealtime=1&limit=10
```
