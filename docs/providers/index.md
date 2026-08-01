# Providers Overview

The Public Transport Integration supports multiple transit providers across Europe, plus Norway and the USA. Each provider has its own API and data format, but the integration normalizes all data into a consistent format.

## Provider Comparison

| Feature | VRR | KVV | HVV | MVV | VVS | VGN | VAG Freiburg | BVG | RMV | VBN OTP | VBN TRIAS | VRN | VVO | DING | AVV | RVV | BSVG | NWL | NVBW | BEG | SBB | ÖBB | Trafiklab | NTA | Transitous | openpublictransport | OTP2 Custom |
|---------|-----|-----|-----|-----|-----|-----|--------------|-----|-----|---------|-----------|-----|-----|------|-----|-----|------|-----|------|-----|-----|-----|-----------|-----|-----------|---------------------|-------------|
| **Region** | NRW | Karlsruhe | Hamburg | Munich | Stuttgart | Nuremberg | Freiburg | Berlin | Frankfurt | Bremen/Niedersachsen | Bremen/Niedersachsen | Rhein-Neckar | Dresden | Ulm | Augsburg | Regensburg | Braunschweig | Westfalen-Lippe | Baden-Württemberg | Bayern | Switzerland | Austria | Sweden | Ireland | Worldwide | Germany (all) | Any OTP2 |
| **API Type** | EFA | EFA | EFA | EFA | EFA | EFA | EFA | FPTF REST | HAFAS REST | OTP REST | TRIAS XML | EFA | EFA | EFA | EFA | EFA | EFA | EFA | EFA | EFA | REST | FPTF REST | REST | GTFS-RT | MOTIS2 | OTP2 GraphQL | OTP2 GraphQL |
| **API Key** | No | No | No | No | No | No | No | No | Yes (free) | Yes (free) | Yes (free) | No | No | No | No | No | No | No | No | No | No | No | Yes (free) | Yes (free) | No | Yes (free²) | Optional |
| **Real-time Data** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | When available | Yes (GTFS-RT) | Depends on server |
| **Delay Information** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | When available | Yes | Depends on server |
| **Platform Info** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | No | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Limited | When available | No | No |
| **Agency/Operator** | No | No | No | No | No | No | No | Yes | Yes | Yes | No | No | No | No | No | No | No | No | No | No | No | Yes | Yes | No | When available | No | No |
| **Alerts/Notices** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | No | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | No | Yes | No | Yes | When available | No | No |
| **Trip Planner** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | No | No | Yes | No | No | No | No | No | No | No | No | No | No | No | No | No | No | No | No | No |
| **Stop Search** | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Geocoded¹ | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Autocomplete | Stop ID | Autocomplete | GraphQL + prefix | GraphQL + prefix |

¹ VBN OTP has no native name-based stop search. The integration geocodes your search term via Nominatim (OpenStreetMap) and finds stops within 500 m of the resolved coordinates.

² API key for the community server is free — [request it here](https://openpublictransport.net/api-key).

### Providers added in 0.1.14

These use the HAFAS "Scotty", HAFAS `mgate.exe`, or Entur transmodel interfaces. None require an API key.

| Provider | Region | API Type | Real-time | Platform | Notices | Stop Search |
|----------|--------|----------|-----------|----------|---------|-------------|
| **NS** | Netherlands | HAFAS Scotty | Yes | Yes | Yes (HIM) | Autocomplete |
| **mobilitéit.lu** | Luxembourg | HAFAS Scotty | Yes | Yes | Yes (HIM) | Autocomplete |
| **Entur** | Norway | OTP transmodel GraphQL | Yes | Yes (quay) | Cancellations | Geocoder |
| **BART** | San Francisco, USA | HAFAS mgate | Yes | Yes | Cancellations | Autocomplete |
| **DART** | Des Moines, USA | HAFAS mgate | Yes | Limited | Cancellations | Autocomplete |
| **Irish Rail** | Ireland | HAFAS mgate | Yes | Yes | Cancellations | Autocomplete |
| **TPG** | Geneva, Switzerland | HAFAS mgate | Yes | Yes | Cancellations | Autocomplete |

### Providers added in 0.1.16

| Provider | Region | API Type | Real-time | Platform | Notices | Stop Search |
|----------|--------|----------|-----------|----------|---------|-------------|
| **[HVV Geofox GTI](hvv-gti.md)** | Hamburg, Germany | GTI (HMAC-signed JSON) | Yes (explicit delay) | Yes, incl. changes | Cancellations, attributes | Autocomplete |

HOCHBAHN's official API on behalf of the HVV. Free credentials, requested by email at
api@hochbahn.de. It exposes delays, cancellations and platform changes that the keyless
[HVV](hvv.md) EFA provider does not — both providers remain available.
Trip planning is not supported on GTI yet; use the EFA `hvv` provider for trip entries.

## Timezone Handling

Each provider uses its local timezone for departure times:

| Provider | Timezone |
|----------|----------|
| VRR | Europe/Berlin |
| KVV | Europe/Berlin |
| HVV | Europe/Berlin |
| HVV Geofox GTI | Europe/Berlin |
| MVV | Europe/Berlin |
| VVS | Europe/Berlin |
| VGN | Europe/Berlin |
| VAG Freiburg | Europe/Berlin |
| BVG | Europe/Berlin |
| RMV | Europe/Berlin |
| VBN OTP | Europe/Berlin |
| VBN TRIAS | Europe/Berlin |
| VRN | Europe/Berlin |
| VVO | Europe/Berlin |
| DING | Europe/Berlin |
| AVV | Europe/Berlin |
| RVV | Europe/Berlin |
| BSVG | Europe/Berlin |
| NWL | Europe/Berlin |
| NVBW | Europe/Berlin |
| BEG | Europe/Berlin |
| SBB | Europe/Zurich |
| TPG | Europe/Zurich |
| ÖBB | Europe/Vienna |
| NS | Europe/Amsterdam |
| mobilitéit.lu | Europe/Luxembourg |
| Entur | Europe/Oslo |
| Irish Rail | Europe/Dublin |
| BART | America/Los_Angeles |
| DART | America/Chicago |
| Trafiklab | Europe/Stockholm |
| NTA | Europe/Dublin |
| Transitous | Per-stop (automatic) |
| openpublictransport | Europe/Berlin |
| OTP2 Custom | Europe/Berlin (or per OTP2 config) |

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

### VBN Transport Modes

VBN is available as two separate provider variants. Both use `Authorization: <key>` (no Bearer prefix).

**VBN TRIAS — PtMode strings:**

| PtMode | Type | Description |
|--------|------|-------------|
| rail | train | Regional and long-distance trains |
| urbanRail | train | S-Bahn |
| metro | subway | Metro/U-Bahn |
| tram | tram | Tram/Straßenbahn |
| bus | bus | City and regional bus |
| coach | bus | Coach/Express bus |
| water | ferry | Ferry |

**VBN OTP — GTFS route modes:**

| Mode | Type | Description |
|------|------|-------------|
| RAIL | train | Regional trains |
| TRAM | tram | Tram/Straßenbahn |
| BUS | bus | City and regional bus |
| COACH | bus | Express/regional bus |
| SUBWAY | subway | Metro/U-Bahn |
| FERRY | ferry | Ferry |

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

### HAFAS Scotty Categories (NS, mobilitéit.lu, ÖBB)

Mapped from the product category (the token after `#` in the board's `prod` attribute), with the HAFAS product-class bitmask as a fallback.

| Category | Type | Description |
|----------|------|-------------|
| ICE / RJ / RJX / TGV | train | High-speed |
| IC / EC / EN / NJ / D | train | Long-distance |
| IR / IRE / RE / REX / CJX | train | Regional express |
| R / RB / S / SB / SPR / TER | train | Regional / suburban |
| U | subway | U-Bahn / metro |
| Tram / STR | tram | Tram |
| Bus / O-Bus | bus | Bus / trolleybus |
| F / Schiff / Fähre | ferry | Ferry |

### HAFAS mgate Categories (BART, DART, Irish Rail, TPG)

Mapped from the product `prodCtx.catOut` label (the `cls` bitmask is intentionally **not** used — its meaning differs per deployment, e.g. `128` is a ferry for ÖBB but *Metro* for BART).

| catOut | Type | Description |
|--------|------|-------------|
| Metro | subway | Metro (e.g. BART) |
| Train / DART / Commuter / InterCity / TER | train | Rail services |
| Tram / T | tram | Tram |
| Bus / B | bus | Bus |
| Ferry / Ship / Boat | ferry | Ferry |

### Entur Transport Modes (Norway)

Mapped from the transmodel `transportMode` of each departure's line.

| transportMode | Type |
|---------------|------|
| rail | train |
| metro | subway |
| tram | tram |
| bus / coach | bus |
| water | ferry |

## API Rate Limiting

The integration implements intelligent rate limiting to prevent overloading provider APIs:

- **Daily limit**: 800 API calls per day (with buffer)
- **Retry logic**: Exponential backoff on errors
- **Timeout**: 10 seconds per API call
- **Max retries**: 3 attempts per update

!!! info
    If rate limits are reached, the integration will create a repair issue in Home Assistant to notify you.
