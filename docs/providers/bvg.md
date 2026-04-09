# BVG (Berliner Verkehrsbetriebe)

BVG is the main public transport operator for Berlin and the surrounding Brandenburg area in Germany.

## Coverage Area

- Berlin
- Brandenburg
- Berlin suburban rail network (S-Bahn)

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://v6.vbb.transport.rest` |
| **API Type** | FPTF REST |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

BVG uses FPTF (Friendly Public Transport Format) product types:

| Product | Type | Description |
|---------|------|-------------|
| subway | subway | U-Bahn |
| suburban | train | S-Bahn |
| tram | tram | Tram/Straßenbahn |
| bus | bus | Bus services |
| ferry | ferry | Ferry (BVG Fähre) |
| express | train | Express trains (ICE, IC, EC) |
| regional | train | Regional trains (RE, RB) |

## Configuration

### Setup Steps

1. Select **BVG** as provider
2. Search for your stop (e.g., "Alexanderplatz")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- S+U Alexanderplatz
- S+U Brandenburger Tor
- S+U Hauptbahnhof
- S+U Potsdamer Platz

## Special Features

### FPTF REST API

BVG uses the FPTF (Friendly Public Transport Format) REST API, which provides a modern JSON-based interface. This differs from the EFA-based providers by using human-readable product names instead of numeric transport classes.

### Comprehensive Coverage

The VBB (Verkehrsverbund Berlin-Brandenburg) API covers all public transport in Berlin and Brandenburg, including:

- **U-Bahn**: 10 underground lines
- **S-Bahn**: Suburban rail network
- **Tram**: Extensive tram network (mostly in eastern Berlin)
- **Bus**: City and regional bus services
- **Ferry**: BVG ferry lines across Berlin waterways

### Real-time Data

Real-time departure data includes delay information, cancellation notices, and platform changes when available.

## API URLs

### Stop Search

```
https://v6.vbb.transport.rest/locations?query=Alexanderplatz&results=10
```

### Departures

```
https://v6.vbb.transport.rest/stops/STOP_ID/departures?duration=60&results=10
```

## Troubleshooting

### No Results for Stop Search

- Try shorter search terms (e.g., "Alexanderplatz" instead of "S+U Alexanderplatz Bhf")
- Berlin stops often have "S+U" prefixes for combined S-Bahn/U-Bahn stations

### Missing Products

If certain transport types are missing, verify that the product filter is not excluding them in your configuration.
