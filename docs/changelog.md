# Changelog

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

!!! info "Total providers: 11"
    The integration now supports VRR, KVV, HVV, MVV, VVS, VGN, VAG Freiburg, BVG, RMV, Trafiklab (Sweden), and NTA (Ireland).

### New Features

- **Configurable delay threshold** (1-30 min, was hardcoded at 5 min)
- **Line filter** - comma-separated filter for specific lines (e.g., `U79, RE5`)
- **Richer departure data** - disruption notices, platform change detection
- **Dynamic version numbers** from git tags

### Improvements

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
