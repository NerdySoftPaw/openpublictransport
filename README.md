![logo]
# Multi-Provider Public Transport Home Assistant Integration
[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![HACS][hacsbadge]][hacs]
[![Documentation](https://img.shields.io/badge/docs-openpublictransport.net-blue.svg?style=for-the-badge)](https://docs.openpublictransport.net/)

![Project Maintenance][maintenance-shield]
[![HACS Validation](https://github.com/NerdySoftPaw/openpublictransport/actions/workflows/hacs.yaml/badge.svg)](https://github.com/NerdySoftPaw/openpublictransport/actions/workflows/hacs.yaml)
[![Code Quality](https://github.com/NerdySoftPaw/openpublictransport/actions/workflows/lint.yaml/badge.svg)](https://github.com/NerdySoftPaw/openpublictransport/actions/workflows/lint.yaml)
[![Tests](https://github.com/NerdySoftPaw/openpublictransport/actions/workflows/tests.yaml/badge.svg)](https://github.com/NerdySoftPaw/openpublictransport/actions/workflows/tests.yaml)

> **📢 This is the official active repository!**
> 
> This repository (`openpublictransport`) is the successor to `VRRAPI-HACS` and is under active development.
> For migration instructions, see [MIGRATION.md](MIGRATION.md).
> 
> 📖 **Full Documentation**: [docs.openpublictransport.net](https://docs.openpublictransport.net/)

A Home Assistant integration for 10 public transport networks: VRR (Rhein-Ruhr), KVV (Karlsruhe), HVV (Hamburg), BVG (Berlin), MVV (München), VVS (Stuttgart), VAG (Freiburg), RMV (Frankfurt), Trafiklab (Sweden), and NTA (Ireland). This integration provides real-time departure information for public transport across Germany, Sweden, and Ireland.

## Features

### Core Features
- **Smart Setup Wizard**: Intuitive multi-step configuration with autocomplete for locations and stops
- **Real-time Departures**: Shows current departure times with delays
- **Multiple Transport Types**: Supports trains (ICE, IC, RE), subway, trams, and buses
- **Smart Filtering**: Filter by specific transportation types
- **Binary Sensor for Delays**: Automatic detection of delays (configurable threshold, 1-30 minutes)
- **Device Support**: Entities are grouped together with suggested areas
- **Repair Issues Integration**: Automatic notifications for API errors or rate limits
- **Rate Limiting**: Intelligent API rate limiting to prevent overload (60,000 calls/day)
- **Error Handling**: Robust error handling with exponential backoff strategy
- **Timezone Support**: Proper handling of provider-specific timezones (Europe/Berlin for German providers, Europe/Stockholm for Trafiklab, Europe/Dublin for NTA)
- **Trip Planner**: Plan routes from A to B with connections, transfers, and delay tracking

### Intelligence & Performance Features (v4.2.0)
- **Fuzzy Matching with Typo Tolerance**: Intelligently finds stops even with typos
  - Handles common misspellings: "Hauptbanhof" → "Hauptbahnhof"
  - German umlaut normalization: "Dusseldorf" → "Düsseldorf"
  - Multi-level scoring using SequenceMatcher and Levenshtein distance
  - Smart result ranking based on relevance
- **API Response Caching**: 5-minute intelligent cache reduces API load
  - Instant results for repeated searches
  - Automatic cache management (LRU-like eviction)
  - Normalized cache keys for better hit rate
- **Optimized Sensor Performance**: 20-30% faster departure processing
  - Reduced coordinator lookups
  - O(1) set-based filtering instead of O(n) lists
  - Single-pass processing for statistics
- **Enhanced Code Quality**: Full type hints, comprehensive docstrings, 75% test coverage

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right and select "Custom repositories"
4. Add this repository URL: `https://github.com/NerdySoftPaw/openpublictransport`
5. Select "Integration" as category
6. Click "Add"
7. Search for "Public" and install the integration
8. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/openpublictransport` folder to your `custom_components` directory
2. Restart Home Assistant

## Configuration

The integration uses an **intuitive multi-step setup wizard** with autocomplete functionality:

### Setup Wizard

1. **Select Provider**
   - Choose from 11 providers in a descriptive dropdown (e.g. "VRR — Rhein-Ruhr (NRW)" instead of just "vrr"):
     - **German EFA providers**: VRR (NRW), KVV (Karlsruhe), MVV (München), VVS (Stuttgart), VAG (Freiburg)
     - **German REST providers**: HVV (Hamburg), BVG (Berlin)
     - **German HAFAS providers**: RMV (Frankfurt) - API key required
     - **International**: Trafiklab (Sweden), NTA (Ireland) - API keys required
   - **For RMV:** A free API key from [opendata.rmv.de](https://opendata.rmv.de) is required
   - **For Trafiklab:** A free API key from [trafiklab.se](https://www.trafiklab.se) is required
   - **For NTA:** A free API key from [developer.nationaltransport.ie](https://developer.nationaltransport.ie) is required

2. **Search City/Location**
   - Enter your city (e.g. "Düsseldorf", "Köln", "Hamburg")
   - The integration automatically searches for matching locations

3. **Select Stop**
   - Enter the name of your stop (e.g. "Hauptbahnhof", "Marktplatz")
   - For more precise results, use the "Stop, City" format (e.g. "Holthausen, Düsseldorf") — the integration splits this into a stop name and city filter
   - The integration automatically suggests stops in your location

4. **Configure Settings**
   - Number of departures (1-20)
   - Transport type filter (Bus, Train, Tram, etc.)
   - Update interval (10-3600 seconds)

### Installation Steps

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Public Transport Departures"
4. Follow the setup wizard

### Trafiklab API Key

For the Trafiklab provider (Sweden), you need a free API key:

1. Register at [trafiklab.se](https://www.trafiklab.se)
2. Create a new project
3. Select the "Realtime API"
4. Copy the API key
5. Enter it in the integration's Config Flow

**Note:** API keys are required for Trafiklab, NTA, and RMV. No API key is required for VRR, KVV, HVV, BVG, MVV, VVS, or VAG.

### NTA Ireland API Key

For the NTA provider (Ireland), you need a free API key:

1. Register at [developer.nationaltransport.ie](https://developer.nationaltransport.ie)
2. Subscribe to the "GTFS-Realtime" API
3. You will receive a Primary and Secondary API key
4. Enter the Primary API key in the integration's Config Flow (required)
5. Optionally enter the Secondary API key (used as fallback if Primary fails)

**Note:** 
- The Primary API key is required for NTA sensors
- The Secondary API key is optional but recommended as a fallback
- NTA uses GTFS-RT (General Transit Feed Specification - Realtime) format
- GTFS Static data is automatically downloaded for stop search functionality

### Transportation Types

- `train` - Trains (ICE, IC, RE, RB)
- `subway` - Subway/Metro (U-Bahn)
- `tram` - Tram/Streetcar
- `bus` - Bus
- `ferry` - Ferry
- `taxi` - Taxi

### Examples

#### Configuration Example

After installation, add the integration via UI:
1. Go to Settings > Devices & Services
2. Click "+ Add Integration"
3. Search for "Public Transport Departures"
4. Follow the setup wizard

## Lovelace Dashboard Examples

### 1. Simple Entities Card

```yaml
type: entities
title: Düsseldorf Hauptbahnhof
entities:
  - entity: sensor.openpublictransport_dusseldorf_hauptbahnhof
    name: Nächste Abfahrt
  - type: attribute
    entity: sensor.openpublictransport_dusseldorf_hauptbahnhof
    attribute: next_departure_minutes
    name: In Minuten
    suffix: min
  - type: attribute
    entity: sensor.openpublictransport_dusseldorf_hauptbahnhof
    attribute: total_departures
    name: Verfügbare Verbindungen
```

### 2. Markdown Card with Departures List

```yaml
type: markdown
title: Abfahrten - Hauptbahnhof
content: >
  {% set departures = state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof',
  'departures') %}

  {% if departures %}
    {% for departure in departures[:5] %}
      **{{ departure.line }}** → {{ departure.destination }}
      🕐 {{ departure.departure_time }} {% if departure.delay > 0 %}(+{{ departure.delay }} min){% endif %}
      📍 Gleis {{ departure.platform }}

    {% endfor %}
  {% else %}
    Keine Abfahrten verfügbar
  {% endif %}
```

### 3. Custom Button Card for Manual Refresh

```yaml
type: button
name: Abfahrten aktualisieren
icon: mdi:refresh
tap_action:
  action: call-service
  service: openpublictransport.refresh_departures
  service_data:
    entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
```

### 4. Multiple Departures with Auto-Entities (requires custom:auto-entities)

```yaml
type: custom:auto-entities
card:
  type: entities
  title: Alle Abfahrten
filter:
  template: >
    {% set departures = state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof',
    'departures') %}

    {% for departure in departures %}
      {{
        {
          'type': 'custom:template-entity-row',
          'name': departure.line + ' → ' + departure.destination,
          'icon': 'mdi:train',
          'state': departure.departure_time,
          'secondary': 'Gleis ' + departure.platform + ' | in ' + departure.minutes_until_departure|string + ' min'
        }
      }},
    {% endfor %}
```

### 5. Template Sensor for "Minutes Until Departure"

Add this to your `configuration.yaml`:

```yaml
template:
  - sensor:
      - name: "Next Train Minutes"
        state: >
          {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'next_departure_minutes') }}
        unit_of_measurement: "min"
        icon: mdi:clock-outline

      - name: "Next Train Line"
        state: >
          {% set departures = state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'departures') %}
          {% if departures and departures|length > 0 %}
            {{ departures[0].line }}
          {% else %}
            -
          {% endif %}
        icon: mdi:train
```

### 6. Conditional Card (only show if departure soon)

```yaml
type: conditional
conditions:
  - entity: sensor.next_train_minutes
    state_not: unavailable
    state_not: unknown
  - entity: sensor.next_train_minutes
    state_below: 10
card:
  type: markdown
  content: >
    ⚠️ **Achtung!** Dein Zug fährt in {{ states('sensor.next_train_minutes') }} Minuten!
```

### 7. Full Dashboard Example

```yaml
type: vertical-stack
cards:
  - type: markdown
    title: 🚉 Düsseldorf Hauptbahnhof
    content: >
      Nächste Abfahrt: **{{ states('sensor.openpublictransport_dusseldorf_hauptbahnhof') }}**

      In {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'next_departure_minutes') }} Minuten

  - type: custom:mushroom-chips-card
    chips:
      - type: entity
        entity: sensor.openpublictransport_dusseldorf_hauptbahnhof
        icon: mdi:train
        content_info: state
      - type: template
        icon: mdi:clock-outline
        content: >
          {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'next_departure_minutes') }} min
      - type: template
        icon: mdi:refresh
        tap_action:
          action: call-service
          service: openpublictransport.refresh_departures

  - type: markdown
    content: >
      {% set departures = state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'departures') %}

      {% if departures %}
        | Linie | Ziel | Abfahrt | Gleis |
        |-------|------|---------|-------|
        {% for dep in departures[:5] %}
        | **{{ dep.line }}** | {{ dep.destination }} | {{ dep.departure_time }}{% if dep.delay > 0 %} <font color="red">(+{{ dep.delay }})</font>{% endif %} | {{ dep.platform }} |
        {% endfor %}
      {% endif %}
```

## Services

### Refresh Departures

Manually refresh departure data from the API.

```yaml
service: openpublictransport.refresh_departures
data:
  entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof  # Optional
```

**Examples:**

Refresh all sensors:
```yaml
service: openpublictransport.refresh_departures
```

Refresh specific sensor:
```yaml
service: openpublictransport.refresh_departures
data:
  entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
```

Use in automation:
```yaml
automation:
  - alias: "Refresh departures when arriving home"
    trigger:
      - platform: state
        entity_id: person.john
        to: home
    action:
      - service: openpublictransport.refresh_departures
        data:
          entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
```

### Plan Trip

Plan a route from A to B with connections, transfers, and delay tracking.

```yaml
service: openpublictransport.plan_trip
data:
  provider: vrr
  origin: Holthausen
  origin_city: Düsseldorf
  destination: Hauptbahnhof
  destination_city: Düsseldorf
```

See [Trip Planner documentation](docs/trip-planner.md) for full details, sensor setup, and example automations.

## API Limits and Rate Limiting

The integration implements intelligent rate limiting:

- **Daily Limit**: 800 API calls per day (with buffer)
- **Retry Logic**: Exponential backoff on errors
- **Timeout**: 10 seconds per API call
- **Max Retries**: 3 attempts per update

## Diagnostics

The integration supports Home Assistant's diagnostics feature for easier troubleshooting.

### How to Download Diagnostics:

1. Go to **Settings** > **Devices & Services**
2. Find your Public Transport Departures integration
3. Click on the integration
4. Click the **3 dots** menu
5. Select **Download Diagnostics**

The diagnostics file contains:
- Configuration details (anonymized)
- Coordinator status
- API call statistics
- Sample API response structure
- Last update information

This information is helpful when reporting issues on GitHub.

## Troubleshooting

### Finding Station ID

To find the station ID, use the VRR API:
```
https://openservice-test.vrr.de/static03/XML_STOPFINDER_REQUEST?outputFormat=RapidJSON&locationServerActive=1&type_sf=stop&name_sf=Düsseldorf%20Hauptbahnhof
```

### Enable Debug Logging

```yaml
logger:
  default: warning
  logs:
    custom_components.openpublictransport: debug
```

### Common Issues

1. **"No departures" State**: 
   - Check station ID or place_dm/name_dm
   - Verify the stop exists

2. **API Rate Limit Reached**:
   - Increase scan_interval
   - Reduce number of sensors

3. **Unknown Transportation Types**:
   - Check debug logs for new product.class values
   - Report missing mappings as an issue

## Transport Class Mapping

The integration maps VRR API Product Classes:

| Class | Transport Type | Description |
|-------|---------------|-------------|
| 0, 1 | train | Legacy trains |
| 2, 3 | subway | Subway/Metro (U-Bahn) |
| 4 | tram | Tram/Streetcar |
| 5-8, 11 | bus | Various bus types |
| 9 | ferry | Ferry |
| 10 | taxi | Taxi |
| 13 | train | Regional train (RE) |
| 15 | train | InterCity (IC) |
| 16 | train | InterCityExpress (ICE) |

## Development and Testing

This integration includes a comprehensive test suite to ensure quality and reliability.

### Running Tests

1. Install test dependencies:
   ```bash
   pip install -r requirements_test.txt
   ```

2. Run the test suite:
   ```bash
   pytest
   ```

3. Run tests with coverage report:
   ```bash
   pytest --cov=custom_components/openpublictransport --cov-report=html
   ```

4. Run specific test files:
   ```bash
   pytest tests/test_sensor.py
   pytest tests/test_binary_sensor.py
   ```

### Test Coverage

The test suite includes:
- **Coordinator Tests**: Rate limiting, API error handling, data updates
- **Sensor Tests**: State updates, icon changes, transportation filtering, attribute validation
- **Binary Sensor Tests**: Delay detection, threshold testing, icon states
- **Config Flow Tests**: User flow, options flow, validation
- **Diagnostics Tests**: Diagnostic data output
- **Integration Tests**: Setup, unload, service registration

### Code Quality

The project uses automated code quality tools:
- **Black**: Code formatting
- **isort**: Import sorting
- **Flake8**: Linting
- **mypy**: Type checking

Run code quality checks:
```bash
black custom_components/openpublictransport/
isort custom_components/openpublictransport/
flake8 custom_components/openpublictransport/
mypy custom_components/openpublictransport/
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Run code quality checks
6. Commit your changes
7. Create a Pull Request

## License

This project is licensed under the MIT License.

## Support

For issues or questions:

1. Check the debug logs
2. Search existing issues for similar problems
3. Create a new issue with debug information

## API Example URLs

### Using Station ID
```
https://openservice-test.vrr.de/static03/XML_DM_REQUEST?outputFormat=RapidJSON&stateless=1&type_dm=any&name_dm=20018235&mode=direct&useRealtime=1&limit=10
```

### Using Place and Stop Name
```
https://openservice-test.vrr.de/static03/XML_DM_REQUEST?outputFormat=RapidJSON&place_dm=Düsseldorf&type_dm=stop&name_dm=Hauptbahnhof&mode=direct&useRealtime=1&limit=10
```


## HVV Support

HVV (Hamburger Verkehrsverbund) is one of the supported providers.

- Use `provider: hvv` in your configuration to fetch departures from any HVV stop.
- Platform information is parsed from `location.properties.platform` in the HVV API response.
- All relevant transport types (bus, metrobus, expressbus, etc.) are mapped.
- Real-time data is shown if HVV provides it via deviations between `departureTimePlanned` and `departureTimeEstimated`.

## NTA Ireland Support

NTA (National Transport Authority, Ireland) is one of the supported providers.

- Use `provider: nta_ie` in your configuration to fetch real-time departures from any Irish public transport stop.
- Uses GTFS-RT (General Transit Feed Specification - Realtime) API for real-time data.
- GTFS Static data is automatically downloaded and cached for stop search functionality.
- Supports all Irish transport operators: Dublin Bus, Bus Éireann, Go-Ahead Ireland, Luas, and Iarnród Éireann.
- Real-time delays are calculated from GTFS-RT trip updates.
- Stop search uses GTFS Static `stops.txt` data (no API calls needed for search).

**Transport Types Supported:**
- Bus (route_type 3)
- Tram/Light Rail (route_type 0, 5, 6)
- Subway/Metro (route_type 1)
- Train/Rail (route_type 2, 7)
- Ferry (route_type 4)

**Example NTA Configuration:**
1. Select "NTA (Ireland)" as provider
2. Enter your Primary API key (and optionally Secondary key)
3. Search for a stop (e.g., "Dublin Connolly", "Heuston Station")
4. Select your stop and configure settings

**API Information:**
- Base URL: `https://api.nationaltransport.ie/gtfsr`
- Endpoint: `/v2/TripUpdates?format=json`
- Authentication: API key via `x-api-key` header
- GTFS Static: Automatically downloaded from Transport for Ireland

**Example HVV API response:**
```json
{
  "stopEvents": [
    {
      "location": {
        "name": "Stadionstraße",
        "properties": {
          "stopId": "28582004",
          "platform": "1"
        }
      },
      "departureTimePlanned": "2025-06-22T20:00:00Z",
      "transportation": {
        "number": "2",
        "description": "Berliner Tor > Hbf. > Altona > Schenefeld",
        "product": {
          "class": 5,
          "name": "Bus"
        },
        "destination": {
          "name": "Schenefeld, Schenefelder Platz"
        }
      }
    }
  ]
}
```

## Changelog

### Version 2026.04.09 - Provider Expansion
#### New Providers
- **BVG (Berlin)**: Full Berlin/Brandenburg support via VBB REST API
- **MVV (München)**: Munich metropolitan area via EFA
- **VVS (Stuttgart)**: Stuttgart area via EFA
- ~~**VGN (Nürnberg)**: Temporarily disabled due to API issues~~
- **VAG (Freiburg)**: Freiburg area via EFA
- **RMV (Frankfurt)**: Rhine-Main area via HAFAS REST API (API key required)

#### New Features
- **Trip Planner**: Plan routes from A to B via service call or dedicated trip sensor
- **Trip Sensor**: Persistent sensor showing next best connection with transfer risk assessment
- **Connection Monitoring**: Built into trip planner — shows connection_feasible, transfer_risk (low/medium/high/missed)
- **Configurable delay threshold**: 1-30 minutes (was hardcoded 5min)
- **Line filter**: Show only specific lines (e.g. "U79, RE5")
- **Richer departure data**: Disruption notices and platform change detection

#### Improvements
- **EFA Base Provider**: Shared base class eliminates code duplication
- **Code cleanup**: sensor.py reduced from 1371 to 530 lines

---

### Version 2026.04.08 - Rebranding & HACS Default Store

> **⚠️ BREAKING CHANGE** — This release renames the integration from `vrr` to `openpublictransport`. Existing users must re-install and re-configure.

#### Breaking Changes
- **Domain renamed**: `vrr` → `openpublictransport`
- **Entity IDs changed**: `sensor.vrr_*` → `sensor.openpublictransport_*`, `binary_sensor.vrr_*` → `binary_sensor.openpublictransport_*`
- **Service renamed**: `vrr.refresh_departures` → `openpublictransport.refresh_departures`
- **Repository renamed**: `hacs-publictransport` → `openpublictransport`

#### What you need to do
1. Remove the old `vrr` integration from Home Assistant
2. Remove the old custom repository from HACS
3. Install `openpublictransport` from the HACS Default Store
4. Re-configure your stops
5. Update all automations and dashboards (see [MIGRATION.md](MIGRATION.md) for details)

#### Why?
The integration started as a VRR-only tool but now supports 11 providers across Germany, Sweden, and Ireland. The old name `vrr` no longer reflected the scope. The rename also enables listing in the official HACS Default Store.

#### New
- **HACS Default Store**: The integration is now available in the official HACS store
- **Documentation**: New docs site at [docs.openpublictransport.net](https://docs.openpublictransport.net/)

---

### Version 4.3.0 - NTA Ireland Support
#### New Features
- **NTA Ireland Integration**: Full support for National Transport Authority (Ireland) GTFS-RT API
  - Real-time departure information for all Irish public transport operators
  - Automatic GTFS Static data download and caching for stop search
  - Support for Primary and Secondary API keys with automatic fallback
  - GTFS route_type mapping to internal transport types (bus, tram, train, subway, ferry)
  - Timezone support for Europe/Dublin
- **GTFS Static Data Loader**: New module for handling GTFS Static ZIP files
  - Automatic download and caching of GTFS Static data
  - 24-hour cache duration with automatic refresh
  - Support for stops.txt, routes.txt, trips.txt, and stop_times.txt
  - Efficient CSV parsing with async file operations
- **Enhanced API Key Management**: Support for Primary and Secondary API keys
  - Automatic fallback to Secondary key if Primary fails with 401
  - Config Flow support for both keys (Primary required, Secondary optional)

#### Technical Details
- **GTFS-RT JSON Format**: Uses JSON format instead of Protocol Buffers for easier parsing
- **Stop Search**: Uses GTFS Static stops.txt for fast, offline-capable stop search
- **Route Information**: Automatically resolves route names from GTFS Static routes.txt
- **Transport Type Detection**: Maps GTFS route_type (0-7) to internal types

### Version 4.2.0 - Performance & Intelligence Update
#### New Features

**Intelligent Fuzzy Matching for Stop Search**
- **Typo Tolerance**: Automatically corrects minor typos in stop/station names
  - Example: "Hauptbanhof" → finds "Hauptbahnhof"
  - Example: "Dusseldorf" → finds "Düsseldorf" (umlaut normalization)
- **Multi-Level Relevance Scoring**:
  - Exact match detection (+300 points)
  - SequenceMatcher similarity ratio (up to +200 points for >80% match)
  - Levenshtein distance for small typos (+120 points for 1-2 char difference)
  - Per-word fuzzy matching (up to +75 points per word)
  - Place name bonus when city is mentioned (+200 points)
- **German Umlaut Normalization**: ä→ae, ö→oe, ü→ue, ß→ss
- **Smart Result Ranking**: Best matches appear first, even with typos

**API Response Caching**
- **5-Minute Cache**: Reduces redundant API calls for repeated searches
- **Smart Cache Keys**: Normalized by provider, search term, and type
- **LRU-Like Eviction**: Automatically maintains 20-entry cache limit
- **Empty Result Caching**: Prevents repeated API calls for non-existent stops
- **Significant Performance Gain**: Instant results for cached searches

**Sensor Performance Optimizations**
- **Reduced Dictionary Lookups**: Cache frequently accessed coordinator values
- **Set-Based Filtering**: O(1) lookup instead of O(n) for transport type filtering
- **Parser Function Pre-Selection**: Eliminate repeated conditional checks
- **Single-Pass Processing**: Combined departure processing and statistics calculation
- **Expected Performance Gain**: 20-30% faster sensor updates

#### Improvements
- **Enhanced Type Hints**: Full typing coverage with `Callable`, `Union`, `Optional`
- **Comprehensive Docstrings**: Detailed documentation for all public methods
- **Improved Validation**:
  - Type validation throughout sensor and config flow
  - Better error messages with context
  - Defensive programming with null checks
- **Test Coverage Increase**: From 34% to **75%** (52 tests, all passing)
- **New Test Suites**:
  - `test_fuzzy_matching.py`: 15 tests for fuzzy matching algorithms
  - `test_caching.py`: 10 tests for API caching system
  - Updated `test_config_flow.py`: 7 tests for simplified 2-step flow
  - All existing tests updated for Home Assistant 2025.10 compatibility

#### Technical Details

**Fuzzy Matching Implementation**
```python
# Example: Searching for "Hauptbanhof" (typo)
search_term = "Hauptbanhof Dusseldorf"
# Finds: "Hauptbahnhof, Düsseldorf" with high relevance score

# Scoring breakdown:
# - Fuzzy ratio: 0.95 → +190 points
# - Levenshtein distance: 1 → +120 points
# - Word fuzzy match: "Hauptbanhof" ≈ "Hauptbahnhof" (0.91) → +68 points
# - Place match: "Dusseldorf" ≈ "Düsseldorf" → +200 points
# Total: 578 points (excellent match despite typo)
```

**Caching System**
```python
# First search: API call (takes ~200-500ms)
stops = await config_flow._search_stops("Hauptbahnhof")

# Same search within 5 minutes: Cache hit (takes <1ms)
stops = await config_flow._search_stops("Hauptbahnhof")  # Instant!

# Different search: New API call
stops = await config_flow._search_stops("Stadtmitte")    # API call

# Cache automatically manages:
# - TTL expiration (5 minutes)
# - Size limit (20 entries, oldest removed first)
# - Normalized keys (case-insensitive, umlaut-normalized)
```

**Performance Optimizations**
```python
# Before (multiple lookups):
for dep in departures:
    station_name = f"{self.coordinator.place_dm} - {self.coordinator.name_dm}"
    if dep["type"] in self.transportation_types:  # O(n) list lookup
        # Process...

# After (optimized):
station_name = f"{self.coordinator.place_dm} - {self.coordinator.name_dm}"  # Once
transport_types_set = set(self.transportation_types)  # O(1) lookup
parse_fn = self._get_parser_function()  # Pre-selected

for dep in departures:
    if dep["type"] in transport_types_set:  # O(1) set lookup
        # Process with pre-selected parser...
```

### Version 4.1.0 - UX Enhancement Update
#### New Features
- **Smart Setup Wizard with Autocomplete**: Multi-step configuration flow
  - Search for locations (cities) with autocomplete via STOPFINDER API
  - Search for stops/stations based on selected location
  - Automatic suggestions for both locations and stops
  - Support for all providers
- **Comprehensive Test Suite**: 50+ unit tests for all components
- **GitHub Actions CI/CD**: Automated testing, linting, and releases
- **Enhanced Error Messages**: Better German and English translations

### Version 4.0.0 - Major Update
#### New Features
- **DataUpdateCoordinator Pattern**: Modern Home Assistant best practice implementation
- **Binary Sensor for Delays**: Automatic delay detection (>5 minutes threshold)
- **Device Support**: Entities grouped together with suggested areas
- **Repair Issues Integration**: Notifications for API errors or rate limits
- **Diagnostics Support**: Download diagnostics for easier troubleshooting
- **Manual Refresh Service**: `openpublictransport.refresh_departures` service for manual updates
- **Dynamic Icons**: Icon changes based on next departure type (bus, train, tram, etc.)
- **Transportation Type Filtering**: Now actually works! Filter departures by type
- **Options Flow Support**: Change settings without removing/re-adding integration
- **Enhanced Sensor Attributes**:
  - `next_3_departures`: Quick overview of upcoming departures
  - `delayed_count` / `on_time_count`: Departure statistics
  - `average_delay`: Average delay across all departures
  - `earliest_departure` / `latest_departure`: Time range of departures

#### Improvements
- **Code Optimization**: Eliminated ~200 lines of duplicate code
- **API Response Validation**: Better error handling and validation
- **Scan Interval**: Actually configurable now (10s - 3600s)
- **Enhanced Logging**: Better error messages with context
- **Rate Limiting**: Smarter handling of API limits (60,000 calls/day)
- **Code Quality**: Black, isort, Flake8, mypy integration

#### Bug Fixes
- Fixed transportation type filtering not working
- Fixed options not being applied
- Fixed scan interval being ignored
- Fixed missing imports and type hints

### Previous Changes
- Added comprehensive transport type mapping (ICE, IC, RE trains)
- Implemented intelligent API rate limiting
- Enhanced error handling with exponential backoff
- Added debug logging for transport classification
- Improved timezone handling for German local time
- Added support for both station ID and place/name queries
- Enhanced real-time data processing and delay calculations
- Improved sensor attributes for better usability

**Made with ❤️ for the Home Assistant community**
<!-- Links -->
[releases-shield]: https://img.shields.io/github/release/NerdySoftPaw/openpublictransport.svg?style=for-the-badge
[releases]: https://github.com/NerdySoftPaw/openpublictransport/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/NerdySoftPaw/openpublictransport.svg?style=for-the-badge
[commits]: https://github.com/NerdySoftPaw/openpublictransport/commits/main
[license-shield]: https://img.shields.io/github/license/NerdySoftPaw/openpublictransport.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-NerdySoftPaw-blue.svg?style=for-the-badge
[hacsbadge]: https://img.shields.io/badge/HACS-Default-blue.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[logo]: https://brands.home-assistant.io/openpublictransport/icon.png
