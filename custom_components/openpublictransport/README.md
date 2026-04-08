# Multi-Provider Public Transport Home Assistant Integration

This integration displays departures for various public transport providers in Home Assistant.

## Setup

- Install via HACS or add as custom_component
- Add integration "Public Transport Departures"
- Select provider: `vrr`, `kvv`, `hvv`, `trafiklab_se` or `nta_ie`
- Enter city and stop name (e.g. Düsseldorf, Elbruchstrasse or Karlsruhe, Essenweinstraße)
- **For Trafiklab (Sweden):** API key from [trafiklab.se](https://www.trafiklab.se) required
- Optional: station_id, number of departures, transport types

## Supported Providers
- **vrr**: Verkehrsverbund Rhein-Ruhr (NRW) - Default
- **kvv**: Karlsruher Verkehrsverbund
- **hvv**: Hamburger Verkehrsverbund
- **trafiklab_se**: Trafiklab Realtime API (Sweden) - **API key required**
- **nta_ie**: National Transport Authority (Ireland) - **API key required**

### Trafiklab API Key

To use the Trafiklab provider (Sweden), you need a free API key:

1. Register at [trafiklab.se](https://www.trafiklab.se)
2. Create a new project
3. Select the "Realtime API"
4. Copy the API key
5. Enter it in the integration's Config Flow

The API key is only required for Trafiklab and NTA sensors. No API key is required for VRR, KVV and HVV.

## Supported Transport Types
- bus
- tram
- subway
- train

## Examples

### KVV (Karlsruhe)
```
sensor:
  - platform: openpublictransport
    provider: kvv
    place_dm: Karlsruhe
    name_dm: Essenweinstraße
    departures: 5
    transportation_types:
      - tram
      - train
```

### HVV (Hamburg)
```
sensor:
  - platform: openpublictransport
    provider: hvv
    place_dm: Hamburg
    name_dm: Hauptbahnhof
    departures: 10
    transportation_types:
      - bus
      - subway
```

### Trafiklab (Sweden)
```
sensor:
  - platform: openpublictransport
    provider: trafiklab_se
    station_id: "740000001"  # Stop ID from Trafiklab
    departures: 10
    transportation_types:
      - bus
      - train
      - tram
```

**Note:** For Trafiklab, you must enter the API key in the Config Flow. You can find the stop ID via the search in the Config Flow.

## Notes
- The integration uses the public APIs of the respective transport associations
- **No API key** is required for VRR, KVV and HVV
- For Trafiklab (Sweden), a **free API key** from [trafiklab.se](https://www.trafiklab.se) is required
- Fields are automatically parsed from the API
- Real-time data is displayed when available
