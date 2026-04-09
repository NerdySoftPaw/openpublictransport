# Changelog

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
