---
hide:
  - toc
---

# Providers Overview

The integration supports 38 transit providers across Europe and the USA. Each has its own API and data format; the integration normalizes all of them into the same entities and attributes.

## Provider Comparison

All 38 providers, one row each. The code below each name is the provider ID — what you
pick in the config flow and what the `plan_trip` action expects.

| Provider | Region | API | Key | RT | Platform | Alerts | Trip | Search |
|----------|--------|-----|-----|:--:|:--------:|:------:|:----:|:------:|
| [VRR](vrr.md)<br>`vrr` | Rhein-Ruhr | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [KVV](kvv.md)<br>`kvv` | Karlsruhe | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [HVV](hvv.md)<br>`hvv` | Hamburg | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [HVV Geofox GTI](hvv-gti.md)<br>`hvv_gti` | Hamburg | GTI | free³ | ✅ | ✅⁴ | ✅ | – | Auto |
| [BVG](bvg.md)<br>`bvg` | Berlin | FPTF | – | ✅ | ✅ | ✅ | – | Auto |
| [MVV](mvv.md)<br>`mvv` | Munich | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [VVS](vvs.md)<br>`vvs` | Stuttgart | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [VGN](vgn.md)<br>`vgn` | Nuremberg | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [VAG](vagfr.md)<br>`vagfr` | Freiburg | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [RMV](rmv.md)<br>`rmv` | Frankfurt | HAFAS | free | ✅ | ✅ | ✅ | – | Auto |
| [VRN](vrn.md)<br>`vrn` | Rhein-Neckar | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [VVO](vvo.md)<br>`vvo` | Dresden | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [DING](ding.md)<br>`ding` | Ulm | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [AVV](avv.md)<br>`avv_augsburg` | Augsburg | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [RVV](rvv.md)<br>`rvv` | Regensburg | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [BSVG](bsvg.md)<br>`bsvg` | Braunschweig | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [NWL](nwl.md)<br>`nwl` | Westfalen-Lippe | EFA | – | ✅ | ✅ | ✅ | ✅ | Auto |
| [NVBW](nvbw.md)<br>`nvbw` | Bad.-Württ. | EFA | – | ✅ | ✅ | ✅ | – | Auto |
| [BEG](beg.md)<br>`beg` | Bavaria | EFA | – | ✅ | ✅ | ✅ | – | Auto |
| [DB](db.md)<br>`db` | Germany | FPTF | – | ✅ | ✅ | ✅ | – | Auto |
| [VBN OTP](vbn.md)<br>`vbn_otp` | Bremen | OTP | free | ✅ | – | ✅ | ✅ | Geo¹ |
| [VBN TRIAS](vbn.md)<br>`vbn_trias` | Bremen | TRIAS | free | ✅ | ✅ | – | – | Auto |
| [openpublictransport](openpublictransport.md)<br>`openpublictransport` | Germany | OTP2 | free² | ✅ | – | – | ✅ | Prefix |
| [SBB](sbb.md)<br>`sbb` | Switzerland | REST | – | ✅ | ✅ | – | – | Auto |
| [TPG](tpg.md)<br>`tpg_ch` | Geneva | mgate | – | ✅ | ✅ | ✅⁵ | – | Auto |
| [ÖBB](oebb.md)<br>`oebb` | Austria | Scotty | – | ✅ | ✅ | ✅ | – | Auto |
| [NS](ns.md)<br>`ns_nl` | Netherlands | Scotty | – | ✅ | ✅ | ✅ | – | Auto |
| [mobilitéit.lu](mobiliteit_lu.md)<br>`mobiliteit_lu` | Luxembourg | Scotty | – | ✅ | ✅ | ✅ | – | Auto |
| [Rejseplanen](rejseplanen.md)<br>`rejseplanen` | Denmark | HAFAS | free | ✅ | ✅⁴ | ✅⁵ | – | Auto |
| [Entur](entur.md)<br>`entur_no` | Norway | OTP | – | ✅ | ✅ | ✅⁵ | – | Geo |
| [Trafiklab](trafiklab.md)<br>`trafiklab_se` | Sweden | REST | free | ✅ | ✅ | – | – | Auto |
| [NTA](nta.md)<br>`nta_ie` | Ireland | GTFS-RT | free | ✅ | ~ | ✅ | – | ID |
| [Irish Rail](irishrail.md)<br>`irishrail_ie` | Ireland | mgate | – | ✅ | ✅ | ✅⁵ | – | Auto |
| [National Rail](national_rail.md)<br>`national_rail` | Great Britain | SOAP | free | ✅ | ✅ | ✅⁵ | – | Auto |
| [BART](bart.md)<br>`bart_us` | San Francisco | mgate | – | ✅ | ✅ | ✅⁵ | – | Auto |
| [DART](dart.md)<br>`dart_us` | Des Moines | mgate | – | ✅ | ~ | ✅⁵ | – | Auto |
| [Transitous](transitous.md)<br>`transitous` | Worldwide | MOTIS2 | – | ~ | ~ | ~ | – | Auto |
| [OTP2 Custom](otp-custom.md)<br>`otp_custom` | Any OTP2 | OTP2 | opt. | ~ | – | – | ✅ | Prefix |

**Reading the table.** ✅ supported · ~ partial or provider-dependent · – not available.
**Key** is `free` where a no-cost key or credential is needed, `opt.` where one is optional.
**RT** is real-time data; delay information comes with it, from the same response.
**Search** is how you find a stop: `Auto` autocomplete, `Geo` geocoded by coordinates,
`ID` stop ID entered by hand, `Prefix` GraphQL prefix search.

**API** column: `EFA` EFA/XML departure monitor · `FPTF` FPTF REST · `HAFAS` HAFAS REST ·
`Scotty` legacy HAFAS Scotty · `mgate` HAFAS `mgate.exe` JSON · `GTI` Geofox GTI (signed JSON) ·
`OTP` OTP REST or transmodel GraphQL · `OTP2` OTP2 GraphQL · `TRIAS` TRIAS XML ·
`GTFS-RT` GTFS realtime feed · `MOTIS2` MOTIS v2 · `SOAP` OpenLDBWS · `REST` provider-specific REST.

Agency and operator names are reported by BVG, RMV, VBN OTP, ÖBB and Trafiklab; the EFA providers
do not expose them.

¹ VBN OTP has no native name-based stop search. The integration geocodes your search term via Nominatim (OpenStreetMap) and finds stops within 500 m of the resolved coordinates.

² API key for the community server is free — [request it here](https://openpublictransport.net/api-key).

³ HVV Geofox GTI is HOCHBAHN's official API on behalf of the HVV. Credentials are free and
requested by email at api@hochbahn.de. It exposes delays, cancellations and platform changes that
the keyless [HVV](hvv.md) EFA provider does not — both providers stay available, and trip planning
runs through the EFA `hvv` provider.

⁴ Platform changes are detected and reported, not just the current platform.

⁵ Cancellations only, not the provider's full service-message feed.

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
