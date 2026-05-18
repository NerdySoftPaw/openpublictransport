# VBN (Verkehrsverbund Bremen/Niedersachsen)

VBN is the transit authority for the Bremen/Niedersachsen region in northern Germany.

## Coverage Area

- Bremen (city and suburbs)
- Bremerhaven
- Surrounding Lower Saxony (Niedersachsen) counties (e.g. Delmenhorst, Verden, Rotenburg)

## Two Provider Variants

VBN is available as **two separate selectable providers**, both using the same API key:

| Provider | Endpoint | Protocol |
|----------|----------|---------|
| **VBN OTP** | `http://gtfsr.vbn.de/api/` | OpenTripPlanner REST |
| **VBN TRIAS** | `https://fahrplaner.vbn.de/triasproxy/` | TRIAS XML (VDV 431-2) |

Choose the variant that matches your API key:

- **OTP key** (labelled "OTP-API-Key" in the VBN welcome e-mail) → select **VBN OTP**
- **TRIAS key** → select **VBN TRIAS**

## API Details

| Property | VBN OTP | VBN TRIAS |
|----------|---------|-----------|
| **API Key** | Required (free) | Required (free) |
| **Timezone** | Europe/Berlin | Europe/Berlin |
| **Quota** | 3,000 transactions/day | 3,000 transactions/day |
| **Real-time** | Yes | Yes |
| **Platform info** | No | Yes |
| **Agency/Operator** | Yes | No |
| **Stop alerts** | Yes | No |

## API Key

### Getting an API Key

1. Send an e-mail to **api@vbn.de**
2. Briefly describe your use case (e.g. "Home Assistant integration for personal use")
3. You will receive an API key by e-mail — VBN may issue separate OTP and TRIAS keys
4. Enter the key during integration setup

!!! note
    The API key is free for non-commercial use. Departure board queries count as 1/5 of a transaction each, so the daily quota of 3,000 transactions effectively covers ~15,000 departure lookups per day.

!!! tip
    Activation may take a few business days after your e-mail request.

### Authentication

The API key is sent as a plain HTTP `Authorization` header (no `Bearer` prefix):

```
Authorization: <your-api-key>
```

## Transport Types

### VBN OTP (OpenTripPlanner GTFS modes)

| OTP Mode | Unified Type | Description |
|----------|-------------|-------------|
| `RAIL` | train | Regional trains |
| `TRAM` | tram | Tram/Straßenbahn (Bremen) |
| `BUS` | bus | City and regional bus |
| `COACH` | bus | Express/regional bus |
| `SUBWAY` | subway | Metro/U-Bahn |
| `FERRY` | ferry | Ferry (Weser-Fähre) |

### VBN TRIAS (TRIAS PtMode strings)

| PtMode | Unified Type | Description |
|--------|-------------|-------------|
| `rail` / `urbanRail` | train | Regional trains, S-Bahn |
| `metro` | subway | Metro/U-Bahn |
| `tram` | tram | Tram/Straßenbahn (Bremen) |
| `bus` / `coach` | bus | City and regional bus |
| `water` | ferry | Ferry (Weser-Fähre) |

## Features by Variant

### VBN OTP

- **Stop search**: Geocodes your search term via Nominatim (OpenStreetMap), then finds nearby OTP stops within 500 m
- **Agency/Operator**: Shown in the `agency` departure attribute (e.g. "Bremer Straßenbahn AG")
- **Stop alerts**: Active service alerts for the stop are attached as `notices` to all departures

### VBN TRIAS

- **Stop search**: Native TRIAS `LocationInformationRequest` — returns direct name matches
- **Platform info**: Platform/track numbers included when provided by VBN

## Configuration

### Setup Steps

1. Select **VBN OTP** or **VBN TRIAS** as provider
2. Enter your API key (from your VBN welcome e-mail)
3. Search for your stop (e.g. "Bremen Hauptbahnhof")
4. Select the stop from the results list
5. Configure the number of departures and transport type filters

### Example Stops

- Bremen Hauptbahnhof
- Bremerhaven Hauptbahnhof
- Bremen Domsheide
- Bremen Hauptbahnhof/ZOB
- Osnabrück Hauptbahnhof

## Troubleshooting

### HTTP 401 / API Key Issues

If the integration shows a 401 error after stop selection:

1. Verify the API key was entered correctly (copy-paste from the VBN e-mail)
2. Confirm you selected the correct variant (OTP key → VBN OTP, TRIAS key → VBN TRIAS)
3. Check that your daily quota has not been exceeded (3,000 transactions/day)
4. Confirm the key has been activated by VBN — this can take a few business days

### No Departures Found

1. Re-run the stop search to verify the stop ID is correct
2. Check that the stop has active services at this time of day
3. Enable debug logging to inspect raw API responses:

```yaml
logger:
  logs:
    custom_components.openpublictransport: debug
```

### VBN OTP: Stop Search Returns No Results

OTP has no native name-based stop search. The integration geocodes your search term via Nominatim (OpenStreetMap) and finds stops within 500 m. If no results appear:

- Use a more specific address (e.g. "Bremen Hauptbahnhof, Bremen" instead of just "Hauptbahnhof")
- The stop may be outside the 500 m search radius — try a more precise location name
