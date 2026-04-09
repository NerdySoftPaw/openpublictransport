# Providers Overview

The Public Transport Integration supports multiple transit providers across Europe. Each provider has its own API and data format, but the integration normalizes all data into a consistent format.

## Provider Comparison

| Feature | VRR | KVV | HVV | MVV | VVS | VGN | VAG Freiburg | BVG | RMV | VRN | VVO | DING | AVV | RVV | BSVG | NWL | NVBW | BEG | Trafiklab | NTA |
|---------|-----|-----|-----|-----|-----|-----|--------------|-----|-----|-----|-----|------|-----|-----|------|-----|------|-----|-----------|-----|
| **Region** | NRW | Karlsruhe | Hamburg | Munich | Stuttgart | Nuremberg | Freiburg | Berlin | Frankfurt | Rhein-Neckar | Dresden | Ulm | Augsburg | Regensburg | Braunschweig | Westfalen-Lippe | Baden-Württemberg | Bayern | Sweden | Ireland |
| **API Type** | EFA | EFA | EFA | EFA | EFA | EFA | EFA | FPTF REST | HAFAS REST | EFA | EFA | EFA | EFA | EFA | EFA | EFA | EFA | EFA | REST | GTFS-RT |
| **API Key** | No | No | No | No | No | No | No | No | Yes (free) | No | No | No | No | No | No | No | No | No | Yes (free) | Yes (free) |
| **Real-time Data** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| **Delay Information** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| **Platform Info** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Limited |
| **Stop Search** | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Stop ID |

## Timezone Handling

Each provider uses its local timezone for departure times:

| Provider | Timezone |
|----------|----------|
| VRR | Europe/Berlin |
| KVV | Europe/Berlin |
| HVV | Europe/Berlin |
| MVV | Europe/Berlin |
| VVS | Europe/Berlin |
| VGN | Europe/Berlin |
| VAG Freiburg | Europe/Berlin |
| BVG | Europe/Berlin |
| RMV | Europe/Berlin |
| VRN | Europe/Berlin |
| VVO | Europe/Berlin |
| DING | Europe/Berlin |
| AVV | Europe/Berlin |
| RVV | Europe/Berlin |
| BSVG | Europe/Berlin |
| NWL | Europe/Berlin |
| NVBW | Europe/Berlin |
| BEG | Europe/Berlin |
| Trafiklab | Europe/Stockholm |
| NTA | Europe/Dublin |

## Transport Type Mapping

Different providers use different internal classification systems. The integration maps these to a unified set of transport types:

### Unified Transport Types

| Type | Description | Icon |
|------|-------------|------|
| `train` | Long-distance and regional trains | mdi:train |
| `subway` | Subway/Metro/U-Bahn | mdi:subway-variant |
| `tram` | Tram/Streetcar | mdi:tram |
| `bus` | All bus services | mdi:bus-clock |
| `ferry` | Ferry/Water transport | mdi:ferry |
| `taxi` | Taxi/On-demand | mdi:taxi |

### VRR/KVV/MVV/VVS/VGN/VAG Transport Classes (EFA)

| Class | Type | Description |
|-------|------|-------------|
| 0, 1 | train | Legacy trains |
| 2, 3 | subway | Subway/Metro |
| 4 | tram | Tram |
| 5-8, 11 | bus | Various bus types |
| 9 | ferry | Ferry |
| 10 | taxi | Taxi |
| 13 | train | Regional (RE) |
| 15 | train | InterCity (IC) |
| 16 | train | ICE |

### HVV Transport Classes (EFA)

| Class | Type | Description |
|-------|------|-------------|
| 0 | train | High-speed trains |
| 1, 2 | subway | U-Bahn |
| 3, 4 | tram | S-Bahn |
| 5-8 | bus | Various bus types (Metrobus, Schnellbus, etc.) |
| 9 | ferry | Hafenfähre (Harbor Ferry) |

### BVG Product Types (FPTF)

| Product | Type | Description |
|---------|------|-------------|
| subway | subway | U-Bahn |
| suburban | train | S-Bahn |
| tram | tram | Tram/Straßenbahn |
| bus | bus | Bus services |
| ferry | ferry | Ferry (BVG Fähre) |
| express | train | Express trains (ICE, IC, EC) |
| regional | train | Regional trains (RE, RB) |

### RMV Categories (HAFAS catOut)

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

### Trafiklab Transport Modes

| Mode | Type |
|------|------|
| TRAIN | train |
| METRO | subway |
| TRAM | tram |
| BUS | bus |
| FERRY | ferry |
| TAXI | taxi |

### NTA GTFS Route Types

| Route Type | Type | Description |
|------------|------|-------------|
| 0, 5, 6 | tram | Tram/Light Rail |
| 1 | subway | Subway/Metro |
| 2, 7 | train | Rail |
| 3 | bus | Bus |
| 4 | ferry | Ferry |

## API Rate Limiting

The integration implements intelligent rate limiting to prevent overloading provider APIs:

- **Daily limit**: 800 API calls per day (with buffer)
- **Retry logic**: Exponential backoff on errors
- **Timeout**: 10 seconds per API call
- **Max retries**: 3 attempts per update

!!! info
    If rate limits are reached, the integration will create a repair issue in Home Assistant to notify you.
