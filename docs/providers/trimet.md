# TriMet (Portland, Oregon)

TriMet provides real-time departures for the Portland metro area via its OpenTripPlanner REST API.

## Coverage Area

- MAX Light Rail
- TriMet buses
- WES Commuter Rail and Portland Streetcar

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://maps.trimet.org/otp_mod` |
| **API Key** | Not required |
| **Timezone** | America/Los_Angeles |
| **Data Format** | OTP REST |

## Configuration

### Setup Steps

1. Select **TriMet — USA (Portland)** as provider
2. Search for your stop (e.g. "Pioneer Courthouse Square, Portland")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Pioneer Courthouse Square, Portland
- Portland Union Station
- Gateway Transit Center, Portland
- Beaverton Transit Center

## Features

- Real-time departures with delay in minutes
- No API key required

!!! note
    Stop search geocodes the name with OpenStreetMap and lists nearby stops — include the city, e.g. "Pioneer Courthouse Square, Portland".
