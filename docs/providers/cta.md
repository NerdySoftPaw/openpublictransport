# CTA (Chicago Transit Authority)

CTA provides real-time departures for Chicago 'L' trains and buses via the official CTA Train Tracker and Bus Tracker APIs.

## Coverage Area

- All 'L' lines: Red, Blue, Brown, Green, Orange, Purple, Pink, Yellow
- All CTA bus routes
- **Not included:** Metra and Pace (use [Transitous](transitous.md) for those)

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://lapi.transitchicago.com/api/1.0/` · `https://www.ctabustracker.com/bustime/api/v3/` |
| **API Key** | **Required** (free) — one key for buses, one for 'L' trains |
| **Timezone** | America/Chicago |
| **Data Format** | CTA Train Tracker / Bus Tracker JSON |

## Getting the API Keys

CTA issues two separate free keys. You need the one for the stops you want to monitor, or both:

- **Bus Tracker key** — create an account at [ctabustracker.com](https://www.ctabustracker.com/), sign in, open **My Account → Developer API** and apply.
- **Train Tracker key** — fill in the application form at [transitchicago.com/developers](https://www.transitchicago.com/developers/).

Enter the Bus Tracker key in the first field and the Train Tracker key in the second field of the config flow.

## Configuration

### Setup Steps

1. Select **CTA — USA (Chicago, API Key)** as provider
2. Enter your Bus Tracker and/or Train Tracker key
3. Search for your stop (e.g. "Clark/Lake")
4. Select the stop and configure departures and filters

Stop search works without a key and finds both 'L' stations and bus stops.

### Example Stops

- Clark/Lake
- Howard
- Michigan & Washington
- Belmont

## Features

- Real-time 'L' arrivals (live predictions; scheduled ones are marked as not real-time)
- Real-time bus predictions with delay and cancellation notices
- Line colours for the 'L'
- Free API keys

!!! warning "New provider"
    This provider was built from the official API documentation and could not yet be tested with real keys.
    Please report any problems on GitHub ([#101](https://github.com/NerdySoftPaw/openpublictransport/issues/101)).
