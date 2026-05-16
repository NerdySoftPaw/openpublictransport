# VBN (Verkehrsverbund Bremen/Niedersachsen)

VBN is the transit authority for the Bremen/Niedersachsen region in northern Germany.

## Coverage Area

- Bremen (city and suburbs)
- Bremerhaven
- Surrounding Lower Saxony (Niedersachsen) counties

## API Details

| Property | Value |
|----------|-------|
| **Endpoint** | `https://fahrplaner.vbn.de/triasproxy/` |
| **API Type** | TRIAS (VDV 431-2) XML |
| **API Key** | Required (free for non-commercial/hobbyist use) |
| **Timezone** | Europe/Berlin |
| **Quota** | 3,000 transactions/day (12,000/month) for hobbyists |

## API Key

### Getting an API Key

1. Send an e-mail to **api@vbn.de**
2. Briefly describe your use case (e.g. "Home Assistant integration for personal use")
3. You will receive an API key by e-mail
4. Enter the key during integration setup in Home Assistant

!!! note
    The API key is free for non-commercial use. Departure board queries count as 1/5 of a transaction each, so the daily quota of 3,000 transactions effectively covers up to ~15,000 departure lookups per day — more than sufficient for home automation use.

!!! tip
    Activation may take a few business days after your e-mail request.

### API Key in Configuration

The API key is passed as the `RequestorRef` field in every TRIAS XML request sent to the VBN endpoint.

## Transport Types

VBN uses standard TRIAS `PtMode` strings which are mapped to the integration's unified transport types:

| PtMode | Unified Type | Description |
|--------|-------------|-------------|
| `rail` | train | Regional and long-distance trains (RE, IC, ICE) |
| `urbanRail` | train | S-Bahn |
| `metro` | subway | Metro/U-Bahn |
| `tram` | tram | Tram/Straßenbahn (e.g. Bremen Straßenbahn) |
| `bus` | bus | City and regional bus |
| `coach` | bus | Coach/Express bus |
| `water` | ferry | Ferry (e.g. Weser-Fähre in Bremen) |

## Configuration

### Setup Steps

1. Select **VBN** as provider
2. Enter your API key (received via e-mail from api@vbn.de)
3. Search for your stop (e.g. "Bremen Hauptbahnhof")
4. Select the stop from the results list
5. Configure the number of departures and transport type filters

### Example Stops

- Bremen Hauptbahnhof
- Bremerhaven Hauptbahnhof
- Bremen Domsheide
- Bremen Hbf (Regionalbahn-Bereich)
- Osnabrück Hauptbahnhof

## Troubleshooting

### API Key Issues

If the integration returns no data or shows connection errors:

1. Verify the API key was entered correctly (copy-paste from the e-mail)
2. Check that your daily quota hasn't been exceeded (3,000 transactions/day)
3. Confirm the key has been activated by VBN — this can take a few business days after your initial e-mail

### No Departures Found

1. Re-run the stop search to verify the stop ID is correct
2. Check that the stop has active services at this time of day
3. Enable debug logging in Home Assistant to inspect the raw TRIAS XML responses:
   ```yaml
   logger:
     logs:
       custom_components.openpublictransport: debug
   ```
