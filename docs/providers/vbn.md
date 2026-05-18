# VBN (Verkehrsverbund Bremen/Niedersachsen)

VBN is the transit authority for the Bremen/Niedersachsen region in northern Germany.

## Coverage Area

- Bremen (city and suburbs)
- Bremerhaven
- Surrounding Lower Saxony (Niedersachsen) counties

## API Details

VBN offers three APIs, all protected by the same API key sent as `Authorization: Bearer <key>`:

| API | Endpoint | Used for |
|-----|----------|---------|
| **TRIAS** (primary) | `https://fahrplaner.vbn.de/triasproxy/` | Stop search, departure boards |
| **OTP** (fallback) | `http://gtfsr.vbn.de/api/` | Stop search, departure boards |
| **HAFAS REST** | `https://fahrplaner.vbn.de/restproxy/2/` | Trip planning (not used by this integration) |

| Property | Value |
|----------|-------|
| **API Key** | Required (free for non-commercial/hobbyist use) |
| **Timezone** | Europe/Berlin |
| **Quota** | 3,000 transactions/day, 12,000/month |

The integration automatically tries TRIAS first. If TRIAS is unavailable, it falls back to the OTP REST API — no configuration required.

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

### API Key Authentication

The API key is sent as an HTTP `Authorization` header on every request:

```
Authorization: Bearer <your-api-key>
```

## Transport Types

| Source | Mode | Unified Type | Description |
|--------|------|-------------|-------------|
| TRIAS | `rail` / `urbanRail` | train | Regional trains, S-Bahn |
| TRIAS | `metro` | subway | Metro/U-Bahn |
| TRIAS | `tram` | tram | Tram/Straßenbahn (Bremen) |
| TRIAS | `bus` / `coach` | bus | City and regional bus |
| TRIAS | `water` | ferry | Ferry (Weser-Fähre) |
| OTP | `RAIL` | train | Regional trains |
| OTP | `TRAM` | tram | Tram |
| OTP | `BUS` | bus | Bus |
| OTP | `FERRY` | ferry | Ferry |

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
- Osnabrück Hauptbahnhof

## Troubleshooting

### HTTP 403 / API Key Issues

If the integration returns no data or shows a 403 error:

1. Verify the API key was entered correctly (copy-paste from the e-mail)
2. Check that your daily quota hasn't been exceeded (3,000 transactions/day)
3. Confirm the key has been activated by VBN — this can take a few business days

### TRIAS vs. OTP Fallback

The integration logs which API is active at `INFO` level. Enable debug logging to see detailed request/response information:

```yaml
logger:
  logs:
    custom_components.openpublictransport: debug
```

### No Departures Found

1. Re-run the stop search to verify the stop ID is correct
2. Check that the stop has active services at this time of day
3. Enable debug logging to inspect raw API responses
