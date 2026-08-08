# Providers Overview

The integration supports 38 transit providers across Europe and the USA. Each has its own API and data format; the integration normalizes all of them into the same entities and attributes.

## Provider Comparison

All 38 providers, one row each. The **ID** is what you pick in the config flow and
what the `plan_trip` action expects.

| Provider | ID | Region | API Type | API Key | Real-time | Platform | Alerts | Trip Planner | Stop Search |
|----------|----|--------|----------|---------|-----------|----------|--------|--------------|-------------|
| [VRR](vrr.md) | `vrr` | Rhein-Ruhr (NRW) | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [KVV](kvv.md) | `kvv` | Karlsruhe | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [HVV](hvv.md) | `hvv` | Hamburg | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [HVV Geofox GTI](hvv-gti.md) | `hvv_gti` | Hamburg (official API) | GTI (signed JSON) | Yes (free)³ | Yes (explicit delay) | Yes, incl. changes | Cancellations, attributes | No | Autocomplete |
| [BVG](bvg.md) | `bvg` | Berlin / Brandenburg | FPTF REST | No | Yes | Yes | Yes | No | Autocomplete |
| [MVV](mvv.md) | `mvv` | Munich | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [VVS](vvs.md) | `vvs` | Stuttgart | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [VGN](vgn.md) | `vgn` | Nuremberg | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [VAG](vagfr.md) | `vagfr` | Freiburg | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [RMV](rmv.md) | `rmv` | Frankfurt / Rhein-Main | HAFAS REST | Yes (free) | Yes | Yes | Yes | No | Autocomplete |
| [VRN](vrn.md) | `vrn` | Rhein-Neckar | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [VVO](vvo.md) | `vvo` | Dresden | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [DING](ding.md) | `ding` | Ulm / Donau-Iller | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [AVV](avv.md) | `avv_augsburg` | Augsburg | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [RVV](rvv.md) | `rvv` | Regensburg | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [BSVG](bsvg.md) | `bsvg` | Braunschweig | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [NWL](nwl.md) | `nwl` | Westfalen-Lippe | EFA | No | Yes | Yes | Yes | Yes | Autocomplete |
| [NVBW](nvbw.md) | `nvbw` | Baden-Württemberg | EFA | No | Yes | Yes | Yes | No | Autocomplete |
| [BEG](beg.md) | `beg` | Bavaria | EFA | No | Yes | Yes | Yes | No | Autocomplete |
| [DB](db.md) | `db` | Germany (nationwide) | FPTF REST | No | Yes | Yes | Yes | No | Autocomplete |
| [VBN OTP](vbn.md) | `vbn_otp` | Bremen / Niedersachsen | OTP REST | Yes (free) | Yes | No | Yes | Yes | Geocoded¹ |
| [VBN TRIAS](vbn.md) | `vbn_trias` | Bremen / Niedersachsen | TRIAS XML | Yes (free) | Yes | Yes | No | No | Autocomplete |
| [openpublictransport](openpublictransport.md) | `openpublictransport` | Germany (nationwide) | OTP2 GraphQL | Yes (free)² | Yes (GTFS-RT) | No | No | Yes | GraphQL + prefix |
| [SBB](sbb.md) | `sbb` | Switzerland | REST | No | Yes | Yes | No | No | Autocomplete |
| [TPG](tpg.md) | `tpg_ch` | Geneva | HAFAS mgate | No | Yes | Yes | Cancellations | No | Autocomplete |
| [ÖBB](oebb.md) | `oebb` | Austria | HAFAS Scotty | No | Yes | Yes | Yes (HIM) | No | Autocomplete |
| [NS](ns.md) | `ns_nl` | Netherlands | HAFAS Scotty | No | Yes | Yes | Yes (HIM) | No | Autocomplete |
| [mobilitéit.lu](mobiliteit_lu.md) | `mobiliteit_lu` | Luxembourg | HAFAS Scotty | No | Yes | Yes | Yes (HIM) | No | Autocomplete |
| [Rejseplanen](rejseplanen.md) | `rejseplanen` | Denmark | HAFAS REST | Yes (free) | Yes | Yes, incl. changes | Cancellations | No | Autocomplete |
| [Entur](entur.md) | `entur_no` | Norway | OTP transmodel GraphQL | No | Yes | Yes (quay) | Cancellations | No | Geocoder |
| [Trafiklab](trafiklab.md) | `trafiklab_se` | Sweden | REST | Yes (free) | Yes | Yes | No | No | Autocomplete |
| [NTA](nta.md) | `nta_ie` | Ireland | GTFS-RT | Yes (free) | Yes | Limited | Yes | No | Stop ID |
| [Irish Rail](irishrail.md) | `irishrail_ie` | Ireland | HAFAS mgate | No | Yes | Yes | Cancellations | No | Autocomplete |
| [National Rail](national_rail.md) | `national_rail` | Great Britain | OpenLDBWS (SOAP) | Yes (free) | Yes | Yes | Cancellations + reasons | No | Autocomplete |
| [BART](bart.md) | `bart_us` | San Francisco, USA | HAFAS mgate | No | Yes | Yes | Cancellations | No | Autocomplete |
| [DART](dart.md) | `dart_us` | Des Moines, USA | HAFAS mgate | No | Yes | Limited | Cancellations | No | Autocomplete |
| [Transitous](transitous.md) | `transitous` | Worldwide | MOTIS2 | No | When available | When available | When available | No | Autocomplete |
| [OTP2 Custom](otp-custom.md) | `otp_custom` | Any OTP2 instance | OTP2 GraphQL | Optional | Depends on server | No | No | Yes | GraphQL + prefix |

Delay information is available wherever real-time data is — the two always come from the same
response, so there is no separate column. Agency/operator names are exposed by BVG, RMV, VBN OTP,
ÖBB and Trafiklab; the EFA providers do not report them.

¹ VBN OTP has no native name-based stop search. The integration geocodes your search term via Nominatim (OpenStreetMap) and finds stops within 500 m of the resolved coordinates.

² API key for the community server is free — [request it here](https://openpublictransport.net/api-key).

³ HVV Geofox GTI is HOCHBAHN's official API on behalf of the HVV. Credentials are free and
requested by email at api@hochbahn.de. It exposes delays, cancellations and platform changes that
the keyless [HVV](hvv.md) EFA provider does not — both providers stay available, and trip planning
runs through the EFA `hvv` provider.

## Timezone Handling

Each provider uses its local timezone for departure times:

| Provider | ID | Timezone |
|----------|----|----------|
| VRR | `vrr` | Europe/Berlin |
| KVV | `kvv` | Europe/Berlin |
| HVV | `hvv` | Europe/Berlin |
| HVV Geofox GTI | `hvv_gti` | Europe/Berlin |
| BVG | `bvg` | Europe/Berlin |
| MVV | `mvv` | Europe/Berlin |
| VVS | `vvs` | Europe/Berlin |
| VGN | `vgn` | Europe/Berlin |
| VAG | `vagfr` | Europe/Berlin |
| RMV | `rmv` | Europe/Berlin |
| VRN | `vrn` | Europe/Berlin |
| VVO | `vvo` | Europe/Berlin |
| DING | `ding` | Europe/Berlin |
| AVV | `avv_augsburg` | Europe/Berlin |
| RVV | `rvv` | Europe/Berlin |
| BSVG | `bsvg` | Europe/Berlin |
| NWL | `nwl` | Europe/Berlin |
| NVBW | `nvbw` | Europe/Berlin |
| BEG | `beg` | Europe/Berlin |
| DB | `db` | Europe/Berlin |
| VBN OTP | `vbn_otp` | Europe/Berlin |
| VBN TRIAS | `vbn_trias` | Europe/Berlin |
| openpublictransport | `openpublictransport` | Europe/Berlin |
| SBB | `sbb` | Europe/Zurich |
| TPG | `tpg_ch` | Europe/Zurich |
| ÖBB | `oebb` | Europe/Vienna |
| NS | `ns_nl` | Europe/Amsterdam |
| mobilitéit.lu | `mobiliteit_lu` | Europe/Luxembourg |
| Rejseplanen | `rejseplanen` | Europe/Copenhagen |
| Entur | `entur_no` | Europe/Oslo |
| Trafiklab | `trafiklab_se` | Europe/Stockholm |
| NTA | `nta_ie` | Europe/Dublin |
| Irish Rail | `irishrail_ie` | Europe/Dublin |
| National Rail | `national_rail` | Europe/London |
| BART | `bart_us` | America/Los_Angeles |
| DART | `dart_us` | America/Chicago |
| Transitous | `transitous` | Per-stop (automatic) |
| OTP2 Custom | `otp_custom` | Europe/Berlin (or per OTP2 config) |

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
