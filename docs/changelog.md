# Changelog

## v2026.8.1 — Trip Planner: reachable connections, correct transfer rating

Requires `python-openpublictransport` 0.1.16.

### Fixes

- **Trip Planner showed a connection that had already left, and rated every connection as
  `missed`** ([#72](https://github.com/NerdySoftPaw/openpublictransport/issues/72)) — three
  separate causes, all fixed:
    - The walk to the platform was rated like a transfer. It ends exactly when the connecting
      vehicle leaves, so every journey EFA prefixes with a footpath (all station-to-station
      trips on HVV, KVV, VRR and the other EFA providers) came out as
      `connection_feasible: false` / `transfer_risk: missed` / `min_transfer_time: 0`.
      Only vehicle-to-vehicle transfers are rated now.
    - Connections that had already departed stayed in the sensor. EFA anchors the requested
      time on the first *vehicle* departure and back-dates the walk, so its first journey is
      regularly already running — those are now dropped, and the next reachable connection is
      the sensor state.
    - **Walking time is now honoured by trip entries.** It shifts the query and filters
      connections you could not reach in time; previously the option applied to departure
      boards only. Changing it — or the scan interval — no longer needs a restart.
- **Transfers across midnight** were reported as `missed`, because the gap was calculated from
  `HH:MM` strings pinned to one fixed date. It is now derived from the full timestamps.

### New Features

- **Trip attributes carry full timestamps and a countdown** — `departure_timestamp`,
  `arrival_timestamp` and `in_minutes`, on the connection itself and on every entry in
  `next_journeys`. Cards and templates can tell a connection that is still ahead from one that
  has left, which `HH:MM` alone did not allow.

---

## v2026.8.0 — Platform data, filters, two entries per station, official HVV API

Requires `python-openpublictransport` 0.1.16.

### Breaking Changes

- **KVV platform values changed** from the readable `"Gleis 3"` to the technical `"3"`, matching
  every other EFA provider. The readable string is still available as the new `platform_name`
  attribute. Update any template or card that compares `platform` against `"Gleis 3"`.

### New Providers

- **HVV Geofox GTI** ([#61](https://github.com/NerdySoftPaw/openpublictransport/issues/61)) —
  HOCHBAHN's official API on behalf of the HVV, alongside the existing keyless `hvv` provider.
  It exposes explicit delays, cancellations and platform changes that the public EFA endpoint
  does not. Credentials are free by email to api@hochbahn.de. Trip planning is not supported on
  GTI yet — use the `hvv` provider for trip entries.

### New Features

- **Platform/track filter** ([#57](https://github.com/NerdySoftPaw/openpublictransport/issues/57)) —
  a third filter next to line and destination, in both the setup wizard and the options flow.
  At many stops the track is a more stable direction selector than the destination name.
  Matching ignores the label, so `3`, `Gleis 3` and `gleis 3` all select the same track.
- **The same station can be added twice** ([#55](https://github.com/NerdySoftPaw/openpublictransport/issues/55)) —
  for example one entry per direction — as long as the two differ in at least one filter. The
  filter is shown in the entry title and device name. Existing entries keep their entity IDs
  and device names exactly as they were.
- **New departure attributes**: `platform_name` (readable label), plus `planned_platform` and
  `platform_changed`, which now actually fire for EFA providers.

### Fixes

- **Platform/track was always empty on EFA providers**
  ([#56](https://github.com/NerdySoftPaw/openpublictransport/issues/56)) — affected VVS, VRR,
  MVV, VGN, VRN, VVO, DING, AVV, RVV, BSVG, NWL and VAG, which all reported `platform: ''`
  while the API had the value.
- **VBN OTP trip planner permanently showed "No connections"**
  ([#59](https://github.com/NerdySoftPaw/openpublictransport/issues/59)) — a leftover argument
  made every stop-coordinate lookup fail. Thanks to @rayphi for finding and fixing this.
- **Diagnostics download failed for Trip Planner entries**
  ([#58](https://github.com/NerdySoftPaw/openpublictransport/issues/58)) with an
  `AttributeError`. Diagnostics are now shape-aware, and trip origin/destination names and API
  keys are redacted.
- **Filters set during setup were silently discarded** — the wizard offered the delay
  threshold, line filter, destination filter, favourite lines and walking time, then dropped
  all five. Until now a filter only took effect if entered again under **Configure**.
- **Reconfigure silently reset every other setting** — moving an entry to a different stop
  reset departures, scan interval, transport types, delay threshold, provider logo and walking
  time to their defaults. The form is now prefilled with the entry's current values.
- **False platform-change events** are no longer emitted from comparing `"3"` against
  `"Gleis 3"`.

---

## v2026.6.2 — Line Colors, Agency Sensor Name, Stop Search Fixes

### New Features

- **Agency name in sensor title** — Sensors are now named `Agency - Stop Name` (e.g. "Karlsruher Verkehrsverbund - Rastatt Kehler Straße") instead of repeating the stop name twice. If no agency is found, only the stop name is shown. Existing entries need to be recreated once.
- **Line colors** — Each departure now includes `line_color` and `line_text_color` attributes (e.g. `#e10098` / `#ffffff`). Lovelace cards can use these for colored line badges.
- **Provider label renamed** — Dropdown now shows `openpublictransport.net (Deutschlandweit, API Key)`.

### Fixes

- **Case-insensitive stop search** — Input like `karlsruhe hauptfriedhof` now automatically also searches for `Karlsruhe Hauptfriedhof`. Abbreviations like `KIT`, `S2`, `ICE` are preserved.
- **GraphQL `nearest` replaces REST endpoint** — The Nominatim geocoding fallback now uses the GraphQL `nearest` query. The REST endpoint `/index/stops` was not exposed on `api.openpublictransport.net`.
- **Nominatim word elimination fallback** — When Nominatim cannot geocode the full search term, progressively simpler queries are tried. `KIT Haupteingang Karlsruhe` falls back to `KIT Karlsruhe` and finds nearby stops correctly.

---

## v2026.6.1 — Renamed to OpenPublicTransport + Application Credentials

### Breaking Changes

- The integration display name changed from "Public Transport Departures" to **OpenPublicTransport** in HACS and Home Assistant.

### New Features

- **API keys stored centrally** — Provider API keys are now stored under **Settings → Integrations → ⋮ → Application credentials**. One key per provider, reused across all sensors for that provider.
- **Automatic migration** — Existing keys are migrated automatically on first start. No manual action required.

---

## v2026.5.3-beta.4 — Bugfixes: API Key 401, Stop Search

### Bugfixes

- **HTTP 401 on sensor polling** — `__init__.py` did not read `opt_api_key` / `otp_custom_api_key` from the config entry. The coordinator was created without credentials, causing every poll to return 401. Fixed for both `openpublictransport` and `otp_custom`.
- **Stop search: "Düsseldorf Elbruchstraße" found nothing** — Inputs like `Düsseldorf Elbruchstraße` or `Elbruchstraße, Düsseldorf` failed because Phase 2 was searching `D-Düsseldorf Elbruchstraße` instead of `D-Elbruchstraße`. New Phase 1b detects city names in the search term and builds the correct prefix. All formats now work: bare stop name, `City Stopname`, `Stopname, City`.
- **Config flow: `custom_url` missing for OTP Custom stop search** — `get_provider()` in `_search_stops()` was not passing `custom_url`, which would have broken stop search for custom OTP instances during setup.

---

## v2026.5.3-beta.3 — openpublictransport Community OTP2 + Custom OTP2 Instance

### New Features

- **openpublictransport provider** — Germany-wide real-time departures via community-hosted OTP2 server at `api.openpublictransport.net`. Data: gtfs.de CC 4.0 (daily update, 461 agencies, 437k stops) + GTFS-RT realtime (25+ Verbünde, every 30s). Requires a free API key — [request here](https://openpublictransport.net/api-key).
- **OTP2 Custom provider** — Connect any self-hosted OpenTripPlanner 2 instance. Provide a base URL and optional X-API-Key. Useful for self-hosting the community server image or running a private GTFS feed.
- **OTPProvider base class** — New `otp.py` with shared OTP2 GraphQL logic: 3-phase stop search (bare name → city-word detection → parallel prefix search → Nominatim fallback), multi-platform stop merging (compound pipe-separated IDs), parallel platform fetch, deduplication.

### Technical Details

- VRR/NRW city-prefix search: gtfs.de stores NRW stops as `D-Elbruchstraße`, `K-Hauptbahnhof`, etc. The integration tries all known city prefixes in parallel when a bare search finds nothing.
- Compound stop IDs: GTFS platform stops are grouped by name (`gtfsde:537545|gtfsde:568685`). All platforms are fetched in parallel and merged per sensor.
- Total providers: **26 → 28**

---

## v2026.5.3 - VBN OTP Trip Planner

### New Features

- **VBN OTP trip planner** — VBN OTP now supports the built-in trip planner (`entry_type = "trip"`). The integration calls the OTP `/plan` endpoint with `TRANSIT,WALK` mode, resolves stop coordinates from the OTP index automatically, and parses up to 3 itineraries into the unified journey format with legs, delay, and transfer risk assessment.

### Improvements

- **Trip planner comparison table** — Added Trip Planner row to the provider comparison table in docs and README.
- **HTTP 204 on `/alerts`** — OTP returns 204 (No Content) when there are no active alerts. Treated silently as "no alerts" instead of logging a warning.

### Bugfixes

- **VBN OTP trip: API key not passed** — The trip config entry did not persist the API key, causing 401 errors on `/index/stops` and `/plan` calls. Fixed: `async_step_trip_settings()` now saves `CONF_VBN_API_KEY` when the provider requires one.

!!! note "VBN TRIAS"
    VBN TRIAS does not support trip planning. TRIAS XML trip requests are not implemented.

---

## v2026.5.2 - VBN Provider (OTP + TRIAS) & New OTPBaseProvider

### New Providers

- **VBN OTP** (`vbn_otp`) — Bremen, Bremerhaven, and surrounding Lower Saxony counties via OpenTripPlanner REST API (`http://gtfsr.vbn.de/api/`). API key required (free, request at api@vbn.de).
- **VBN TRIAS** (`vbn_trias`) — Same region via TRIAS XML API (`https://fahrplaner.vbn.de/triasproxy/`). Same API key (or a separate TRIAS key from VBN).

Both providers use `Authorization: <key>` (plain header, no Bearer prefix). Choose the variant that matches the key VBN issued you.

### New Architecture

- **OTPBaseProvider** (`otp_base.py`) — Base class for OpenTripPlanner REST API providers, analogous to `TRIASBaseProvider`. Handles Nominatim geocoding for stop search, stoptimes + routes fetch, alerts, and `parse_departure`. Subclasses only define `otp_base_url`, `provider_id`, `provider_name`, and optional `_auth_headers()`.
- **`_extra_headers()` hook** in `TRIASBaseProvider` — lets subclasses inject HTTP auth headers without modifying the base class.

### New Features (VBN OTP)

- **Agency/Operator** — Operator name (e.g. "Bremer Straßenbahn AG") extracted from the OTP routes endpoint and exposed as `agency` on every departure.
- **Stop alerts** — Active service alerts fetched from `/index/stops/{id}/alerts` and attached as `notices` to all departures at the stop.

### Improvements

- **Alphabetical provider order** — All 26 providers sorted A–Z in the dropdown and documentation.
- **Provider comparison table** — Added Agency/Operator and Alerts/Notices rows across all providers.

### Documentation

- Provider docs: `docs/providers/vbn.md` — both API variants, correct `Authorization: <key>` header format, per-variant feature table, quotas, troubleshooting.
- Provider count updated to 26 across README and docs.

!!! info "Total providers: 26"
    VBN joins as two separate selectable variants (OTP + TRIAS) for a total of 26 provider options.

---

## v2026.4.16 - Deutsche Bahn, TRIAS Protocol, New Logo & Website

### New Provider

- **DB (Deutsche Bahn)** - All of DB's long-distance and regional network (ICE, IC, RE, RB, S-Bahn) via community REST API. No API key required. Note: this API is community-maintained and may experience occasional downtime.

### New Architecture

- **FPTF Base Provider** (`fptf_base.py`) - Shared base class for transport.rest APIs. BVG refactored from 194 to 33 lines. Any future FPTF provider only needs API_BASE + PRODUCT_MAPPING.
- **TRIAS Base Provider** (`trias_base.py`) - Full implementation of the VDV 431-2 TRIAS XML protocol for stop search and departure boards. Ready for agencies offering TRIAS endpoints (VBN, NVBW-TRIAS, SBB-TRIAS, etc.).

### Website & Branding

- New logo: train + departure board + transit map design
- Landing page live at [openpublictransport.net](https://openpublictransport.net)
- 18 real screenshots in documentation (config flow + dashboard layouts)
- Documentation restyled with gold brand colors
- Vercel deploy hook: website auto-rebuilds on new release

### Documentation

- README completely rewritten (940 → 140 lines)
- Migration guide: clear separation of both migrations (VRRAPI→hacs-publictransport vs hacs-publictransport→openpublictransport)
- All provider lists updated to 24 providers
- Sensors page updated to 7 entity types

!!! info "Total providers: 24"
    DB Deutsche Bahn joins as the 24th provider. TRIAS base class ready for more.

---

## v2026.04.12 - Transitous, SBB, ÖBB, Multi-Stop & More

### New Providers

- **Transitous** - Worldwide public transport via MOTIS2 (Community, Beta). Aggregated GTFS/GTFS-RT data, no API key required. Covers stops globally.
- **SBB** - Swiss Federal Railways / all Swiss public transport via transport.opendata.ch, no API key required.
- **ÖBB** - Austrian Federal Railways / all Austrian public transport via FPTF REST API, no API key required.

### New Features

- **Multi-Stop Sensor** - Combine departures from multiple stops into a single sensor. Configure via "Multi-Stop" entry type in the setup wizard.
- **Favorite Lines** - Mark lines as favorites; they appear first in departure lists.
- **Walking Time** - Configure 0-30 min walking time to your stop; departures that can't be reached in time are hidden automatically. Available in both initial setup and options flow.
- **`check_delays` Service** - Query delayed departures with a configurable `delay_threshold` (default 5 min) and optional `line` filter. Fires an `openpublictransport_delay_alert` event with `entity_id`, `delayed_count`, `max_delay`, `lines`, and `departures`.
- **`announce_departure` Service** - Returns a spoken-language departure string for use with any TTS integration. Accepts `entity_id` and optional `index` (default 0 = next departure).
- **Statistics Sensor** - New `sensor.*_statistics` entity per stop. State is overall punctuality (%). Attributes include per-line stats: `total`, `on_time`, `punctuality`, `average_delay`. Delays <= 2 min count as on-time.
- **VGN re-enabled** - The VGN (Nuremberg) provider is available again.

!!! info "Total providers: 23"
    The integration now supports 23 transit networks across Germany, Switzerland, Austria, Sweden, Ireland, and worldwide (via Transitous).

---

## v2026.04.11 - Batch 1+2 Provider Expansion

### New Providers

- **VRN** - Rhein-Neckar / Mannheim, Heidelberg (EFA)
- **VVO** - Oberelbe / Dresden (EFA)
- **DING** - Donau-Iller / Ulm (EFA)
- **AVV** - Augsburg (EFA, provider ID: `avv_augsburg`)
- **RVV** - Regensburg (EFA)
- **BSVG** - Braunschweig (EFA)
- **NWL** - Westfalen-Lippe / Dortmund, Münster, Bielefeld (EFA)
- **NVBW** - Baden-Württemberg statewide (EFA)
- **BEG** - Bayern statewide (EFA)

!!! info "Total providers: 19"
    The integration now supports 19 transit networks across Germany, Sweden, and Ireland. All new providers use the EFA API and require no API key.

---

## v2026.04.10 - Custom Lovelace Card

### New

- **Custom Lovelace Card**: Dedicated [openpublictransport-card](https://github.com/NerdySoftPaw/openpublictransport-card) with table, compact, and trip layouts -- available as a separate HACS plugin

---

## v2026.04.09 - Provider Expansion & New Features

### UX Improvements

- **Descriptive provider dropdown**: Provider selector now shows full names with regions (e.g. "VRR — Rhein-Ruhr (NRW)") instead of short codes
- **Smart stop search**: Entering "Holthausen, Düsseldorf" automatically splits into stop name + city filter for more accurate results
- **"New search" option**: Results dropdown includes a "New search" entry to start over without clearing the field manually
- **Search term in results**: The results description shows your original search term for reference

### New Providers

- **BVG** - Berlin and Brandenburg (FPTF REST API)
- **MVV** - Munich metropolitan area (EFA)
- **VVS** - Stuttgart area (EFA)
- **VGN** - Nuremberg greater area (EFA)
- **VAG** - Freiburg im Breisgau (EFA)
- **RMV** - Frankfurt/Rhine-Main area (HAFAS REST API)

!!! info "Providers at v2026.04.09: 11"
    VRR, KVV, HVV, MVV, VVS, VGN, VAG Freiburg, BVG, RMV, Trafiklab (Sweden), and NTA (Ireland).

### New Features

- **Trip Planner** - Plan routes from A to B via service call or dedicated trip sensor
- **Trip Sensor** - Persistent sensor showing next best connection with transfer risk assessment
- **Connection Monitoring** - Built into trip planner: shows `connection_feasible`, `transfer_risk` (low/medium/high/missed)
- **Configurable delay threshold** (1-30 min, was hardcoded at 5 min)
- **Line filter** - comma-separated filter for specific lines (e.g., `U79, RE5`)
- **Richer departure data** - disruption notices, platform change detection
- **Dynamic version numbers** from git tags

### Improvements

- **Smart Polling** - automatically reduces polling at night (1:00-4:30) and when no departures are available, saves ~30% API calls
- **EFA Base Provider extracted** - new EFA-based providers need ~50 lines of code instead of ~200
- **sensor.py legacy code cleanup** - reduced from 1371 to 530 lines, test coverage improved from 32% to 82%

!!! info "No Breaking Changes"
    All changes in v2026.04.09 are additive.

---

## v2026.04.08 - Rebranding to openpublictransport

!!! warning "Breaking Change: Full Rebranding"
    This release renames the integration from `vrr` to `openpublictransport`. All entity IDs, services, and the component folder change. Existing users must re-configure.

### Breaking Changes

- **Domain renamed**: `vrr` → `openpublictransport`
- **Entity IDs changed**: `sensor.vrr_*` → `sensor.openpublictransport_*`
- **Service renamed**: `vrr.refresh_departures` → `openpublictransport.refresh_departures`
- **Repository renamed**: `hacs-publictransport` → `openpublictransport`

### Migration Guide

See [Migration Guide](migration.md) for step-by-step upgrade instructions.

---

## v2026.01.24 and earlier

See [GitHub Releases](https://github.com/NerdySoftPaw/openpublictransport/releases) for older versions.
