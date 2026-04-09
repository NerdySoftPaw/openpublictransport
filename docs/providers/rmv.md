# RMV (Rhein-Main-Verkehrsverbund)

RMV is the transit authority for the Frankfurt/Rhine-Main metropolitan area in Hesse, Germany.

## Coverage Area

- Frankfurt am Main
- Wiesbaden
- Darmstadt
- Mainz
- Offenbach
- And surrounding areas

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://www.rmv.de/hapi/` |
| **API Type** | HAFAS REST |
| **API Key** | Required (free) |
| **Timezone** | Europe/Berlin |

## API Key

### Getting an API Key

1. Register at [opendata.rmv.de](https://opendata.rmv.de)
2. Request access to the HAFAS REST API
3. You will receive an API key via email
4. Enter the API key during integration setup

!!! note
    The API key is free but required. Registration may take a few business days for approval.

### API Key in Configuration

The API key is stored securely in your Home Assistant configuration and is passed as an `accessId` parameter in all API requests.

## Transport Types

RMV uses the HAFAS `catOut` (category output) field for transport classification:

| catOut | Type | Description |
|--------|------|-------------|
| ICE | train | ICE (InterCity Express) |
| IC | train | IC/EC (InterCity/EuroCity) |
| RE | train | Regional Express |
| RB | train | Regionalbahn |
| S | train | S-Bahn |
| U | subway | U-Bahn |
| Tram | tram | Tram/Straßenbahn |
| Bus | bus | Bus services |

## Configuration

### Setup Steps

1. Select **RMV** as provider
2. Enter your API key
3. Search for your stop (e.g., "Frankfurt Hauptbahnhof")
4. Select the stop from the list
5. Configure departure count and filters

### Example Stops

- Frankfurt Hauptbahnhof
- Konstablerwache
- Wiesbaden Hbf
- Darmstadt Hauptbahnhof

## Special Features

### HAFAS REST API

RMV uses the HAFAS REST API, which differs from the EFA-based providers. HAFAS provides a different data structure with transport categories identified by their `catOut` string rather than numeric class IDs.

### Comprehensive Network

The Rhine-Main area has one of Germany's most extensive transit networks:

- **S-Bahn**: 9 S-Bahn lines connecting the region
- **U-Bahn**: Frankfurt's underground network
- **Tram**: Tram lines in Frankfurt and surrounding cities
- **Bus**: Extensive bus network
- **Regional trains**: RE and RB services throughout Hesse

### Long-Distance Trains

Frankfurt Hauptbahnhof is one of Germany's busiest rail hubs. The RMV API includes ICE and IC departures, making it useful for tracking long-distance train connections.

### Real-time Data

HAFAS provides real-time data through the `rtTime` and `rtDate` fields, with delays calculated as the difference between scheduled and real-time departure times.

## API URLs

### Stop Search

```
https://www.rmv.de/hapi/location.name?accessId=YOUR_API_KEY&input=Frankfurt%20Hauptbahnhof&format=json
```

### Departures

```
https://www.rmv.de/hapi/departureBoard?accessId=YOUR_API_KEY&id=STOP_ID&format=json&duration=60
```

## Troubleshooting

### API Key Issues

If you get a 401 or 403 error:

1. Verify your API key is correct
2. Check that your key has been activated (may take a few days after registration)
3. Ensure you are using the HAFAS REST API key from opendata.rmv.de

### No Departures Found

If no departures are returned:

1. Verify the stop ID is correct
2. Check that the stop has active services at this time
3. Enable debug logging to see API responses
