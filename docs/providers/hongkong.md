# Hong Kong (KMB / MTR)

Real-time arrivals for Hong Kong KMB / LWB buses and MTR trains from the government open data APIs (data.gov.hk).

## Coverage Area

- KMB and Long Win Bus (LWB) — all stops
- MTR heavy rail lines including East Rail, Tuen Ma and Airport Express
- **Not yet included:** Citybus, MTR Light Rail

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://data.etabus.gov.hk/v1/transport/kmb/ · https://rt.data.gov.hk/v1/transport/mtr/` |
| **API Key** | Not required |
| **Timezone** | Asia/Hong_Kong |
| **Data Format** | data.gov.hk REST |

## Configuration

### Setup Steps

1. Select **Hong Kong — KMB / MTR** as provider
2. Search for your stop (e.g. "Admiralty")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Admiralty
- Tsim Sha Tsui (Tsuen Wan Line)
- Central (Island Line)
- MEI FOO BUS TERMINUS

## Features

- Real-time departures (predictions)
- Platform information
- No API key required

!!! note
    Stop names match in English and Chinese. Outside service hours (around 01:00–06:00) KMB and MTR return no arrivals.
