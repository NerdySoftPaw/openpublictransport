# National Rail (UK)

!!! info "API Key Required"
    National Rail uses the **OpenLDBWS** (Live Departure Boards Web Service) SOAP API.
    A free access token is required — register at [realtime.nationalrail.co.uk/OpenLDBWS](https://realtime.nationalrail.co.uk/OpenLDBWS).

## Coverage Area

- All National Rail services across Great Britain
- Long-distance (LNER, GWR, Avanti, CrossCountry, etc.)
- Regional and commuter services
- Eurostar (via domestic stops)

## API Details

| Property | Value |
|----------|-------|
| **Endpoint** | `https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx` |
| **Protocol** | SOAP / XML |
| **API Key** | Required (free, 100k calls/month) |
| **Timezone** | Europe/London |
| **Transport Types** | Train only |

## Getting an API Token

1. Go to [realtime.nationalrail.co.uk/OpenLDBWS](https://realtime.nationalrail.co.uk/OpenLDBWS)
2. Click **Register** and create an account
3. You will receive an access token by email
4. Enter this token during integration setup

!!! tip
    The free tier allows 100,000 calls per month — more than sufficient for personal Home Assistant use.

## Configuration

### Setup Steps

1. Select **National Rail — UK** as provider
2. Enter your OpenLDBWS access token
3. Search for your station (name or partial name, e.g. "King's Cross" or "Leeds")
4. Select from results and configure departure count

### Station Search

Station search uses the **Overpass API** (OpenStreetMap) to find UK railway stations with their 3-letter CRS codes. The search is case-insensitive and matches partial names.

| What you type | What it finds |
|---------------|---------------|
| `kings cross` | London King's Cross (KGX) |
| `leeds` | Leeds (LDS) |
| `manchester piccadilly` | Manchester Piccadilly (MAN) |
| `victoria` | London Victoria (VIC), Birmingham New Street Victoria, … |

!!! tip
    If results are ambiguous, add the city name to narrow down (e.g., "Manchester Piccadilly" instead of "Piccadilly").

## Transport Types

National Rail is a **train-only** provider. All departures are classified as `train`.

The line badge shows the **operator code** (2 letters):

| Code | Operator |
|------|----------|
| GR | LNER |
| GW | Great Western Railway |
| VT | Avanti West Coast |
| SW | South Western Railway |
| SN | Southern |
| LM | West Midlands Trains |
| XC | CrossCountry |
| EM | East Midlands Railway |

## Realtime Data

OpenLDBWS provides live departure information directly from Darwin, the National Rail realtime data feed:

- **On time**: No delay, realtime confirmed
- **HH:MM**: Estimated departure time (with calculated delay in minutes)
- **Delayed**: Delay confirmed but no estimate yet
- **Cancelled**: Service cancelled (with reason if available)

## Troubleshooting

### No results in station search

- The station name must be an OSM-recognized UK railway station
- Try searching with the full official station name
- If still no results, enter the 3-letter CRS code directly (e.g., `KGX` for King's Cross)

### HTTP 401 / Unauthorized

Your access token is invalid or expired. Re-register at [realtime.nationalrail.co.uk/OpenLDBWS](https://realtime.nationalrail.co.uk/OpenLDBWS).

### API offline on Sunday mornings

National Rail's OpenLDBWS may have brief maintenance windows. If queries fail around 02:00–05:00 UK time, retry after a few minutes.
