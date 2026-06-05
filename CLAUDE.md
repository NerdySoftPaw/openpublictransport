# CLAUDE.md — OpenPublicTransport HA Core Submission

## Project Goal

Prepare the custom integration `openpublictransport` for submission to
**Home Assistant Core** (`home-assistant/core`). Every task below is derived
from the official [Bronze Quality Scale](https://developers.home-assistant.io/docs/integration_quality_scale/rules/)
and the Core contribution guide.

---

## Repository Layout

```
custom_components/openpublictransport/
├── __init__.py            Entry setup, 4 services, credential migration
├── manifest.json          Domain metadata and pip requirements
├── const.py               All constants, provider IDs, API URLs
├── config_flow.py         ConfigFlow (1638 lines) + OptionsFlow
├── sensor.py              DataUpdateCoordinator + MultiProviderSensor
├── binary_sensor.py       Delay binary sensor
├── calendar.py            Departure calendar entity
├── event.py               Disruption / platform-change event entity
├── camera.py              PNG departure board camera entity
├── statistics.py          PunctualitySensor (CoordinatorEntity)
├── trip_sensor.py         Trip-planning coordinator + sensor
├── trip.py                async_plan_trip dispatcher (OTP2 / EFA)
├── multi_stop.py          Merged multi-stop sensor
├── data_models.py         UnifiedDeparture, UnifiedStop, UnifiedTransportType
├── parsers.py             parse_departure_generic + helpers
├── diagnostics.py         async_get_config_entry_diagnostics
├── application_credentials.py  ApplicationCredentialsAuthImplementation
├── services.yaml          Action schema docs (all 4 actions)
├── strings.json           English base translations + data_description
├── translations/          de, en, fr, nl, it, pl, sv
└── providers/
    ├── __init__.py        get_provider() factory + register_provider()
    ├── base.py            BaseProvider ABC
    ├── efa_base.py        EFA/XML base → VRR KVV HVV MVV VVS VGN VAG VRN VVO
    ├── trias_base.py      TRIAS/SOAP base → RMV NWL NVBW
    ├── otp_base.py        OTP2 REST/GraphQL base → OPT VBN OTP_CUSTOM
    ├── fptf_base.py       FPTF REST base → Transitous
    └── [24 concrete provider modules]

tests/
├── conftest.py
├── test_init.py
├── test_config_flow.py        ← needs heavy expansion (see task 8)
├── test_sensor.py
├── test_binary_sensor.py
├── test_diagnostics.py
├── test_parsers.py
├── test_providers.py
├── test_caching.py
└── test_fuzzy_matching.py
```

---

## How to Run Tests

```bash
# Install test deps (once)
pip install pytest pytest-homeassistant-custom-component pytest-asyncio aiofiles \
    gtfs-realtime-bindings

# Run the full test suite
pytest tests/ -v

# Run a single file
pytest tests/test_config_flow.py -v

# Run with coverage
pytest tests/ --cov=custom_components/openpublictransport --cov-report=term-missing
```

The test framework is `pytest-homeassistant-custom-component`. Fixtures are in
`tests/conftest.py`. The `auto_enable_custom_integrations` autouse fixture
(conftest.py:100) is required — do not remove it.

---

## Architecture Notes

### Data flow
```
ConfigEntry.data / options
  └── PublicTransportDataUpdateCoordinator (sensor.py)
        ├── provider_instance = get_provider(provider_id, hass, ...)
        ├── _async_update_data() → provider_instance.fetch_departures()
        └── CoordinatorEntity subclasses (sensor, binary_sensor, calendar,
                                          event, camera, statistics)
```

### Provider seam (THE key coupling to break)
Every `BaseProvider` currently receives `hass: HomeAssistant` and calls
`async_get_clientsession(hass)` internally. That single import is what ties
the entire `providers/` tree to HA. Replacing it with `session: aiohttp.ClientSession`
is the first step of the PyPI extraction (Task 3).

### Runtime storage (current vs target)
```python
# CURRENT (wrong)
hass.data[DOMAIN][f"{entry.entry_id}_coordinator"] = coordinator

# TARGET (Task 4)
entry.runtime_data = coordinator
# Then in every platform:
coordinator = entry.runtime_data
```

### Service registration (current vs target)
```python
# CURRENT (wrong) — inside async_setup_entry, runs once per entry
hass.services.async_register(DOMAIN, "refresh_departures", handle_refresh, ...)

# TARGET (Task 7) — inside async_setup, runs once per HA start
async def async_setup(hass, config):
    hass.data.setdefault(DOMAIN, {})
    hass.services.async_register(DOMAIN, "refresh_departures", ...)
    ...
    return True
```

---

## Prioritised Task List

Work items are ordered by dependency. Complete them in sequence unless
noted as parallelisable.

---

### TASK 1 — Replace `pytz` with `zoneinfo` [S]

**Why:** HA Core bans third-party timezone libs. `zoneinfo` is stdlib (Python 3.9+).

**Files to touch:**
- `manifest.json:16` — remove `"pytz"` from `requirements`
- Grep for `import pytz` and `pytz.timezone(` across all provider files
- Replace with `from zoneinfo import ZoneInfo` and `ZoneInfo("Europe/Berlin")`

**Pattern:**
```python
# Before
import pytz
tz = pytz.timezone("Europe/Berlin")

# After
from zoneinfo import ZoneInfo
tz = ZoneInfo("Europe/Berlin")
```

---

### TASK 2 — Fix `action-setup`: move services to `async_setup` [S]

**Why:** Services registered in `async_setup_entry` get re-registered (and the
handler replaced) on every additional config entry. HA rule requires one-time
registration.

**Files to touch:** `__init__.py`

**Steps:**
1. Move the four `hass.services.async_register(...)` blocks (lines 256, 301,
   346, 448) and their handler definitions (`handle_refresh`, `handle_plan_trip`,
   `handle_check_delays`, `handle_announce`) into `async_setup`.
2. The handlers use `hass` (available in `async_setup` scope) — no other changes
   needed to make them work; they already iterate `hass.data[DOMAIN]` and
   `entity_registry` dynamically.
3. Keep the removal block in `async_unload_entry` (lines 478–486) — it already
   guards on last-entry removal, which is correct.

---

### TASK 3 — Extract `python-openpublictransport` PyPI library [L]

**Why:** `dependency-transparency` rule. All API logic must live in a pip-installable
library, not bundled inside the integration.

#### 3a — Create new repo / package structure

```
python-openpublictransport/
├── src/openpublictransport/
│   ├── __init__.py            (get_provider, list_providers, register_provider)
│   ├── models.py              (UnifiedDeparture, UnifiedStop, UnifiedTransportType)
│   ├── parsers.py             (parse_departure_generic)
│   └── providers/
│       ├── base.py
│       ├── efa_base.py
│       ├── trias_base.py
│       ├── otp_base.py
│       ├── fptf_base.py
│       └── [24 concrete modules]
├── pyproject.toml
└── tests/
```

#### 3b — Break the HA coupling in BaseProvider

```python
# providers/base.py — BEFORE
from homeassistant.core import HomeAssistant

class BaseProvider(ABC):
    def __init__(self, hass: HomeAssistant, api_key=None, ...):
        self.hass = hass

# providers/base.py — AFTER (no HA imports)
import aiohttp

class BaseProvider(ABC):
    def __init__(self, session: aiohttp.ClientSession, api_key=None,
                 api_key_secondary=None, custom_url=None):
        self.session = session
        self.api_key = api_key
        self.api_key_secondary = api_key_secondary
        self.custom_url = custom_url
```

Every provider that calls `async_get_clientsession(self.hass)` must change to
`self.session`. Search pattern: `async_get_clientsession`.

#### 3c — Update `providers/__init__.py` factory signature

```python
# Before
def get_provider(provider_id, hass, api_key=None, ...):

# After
def get_provider(provider_id, session: aiohttp.ClientSession, api_key=None, ...):
```

#### 3d — Update the integration to inject the session

In `sensor.py` (coordinator `__init__`):
```python
from homeassistant.helpers.aiohttp_client import async_get_clientsession

session = async_get_clientsession(hass)
self.provider_instance = get_provider(provider, session, api_key=api_key, ...)
```

Same pattern in `config_flow.py` wherever `get_provider` is called.

#### 3e — Move `data_models.py` and `parsers.py` into the library

These have zero HA dependencies today — copy verbatim. Update all imports in
the integration from `.data_models` to `openpublictransport.models` (or whatever
the library package name is).

#### 3f — Publish and add to manifest

```json
"requirements": ["python-openpublictransport==0.1.0", "aiofiles", "gtfs-realtime-bindings>=1.0.0"]
```

Remove `pytz` (done in Task 1).

---

### TASK 4 — Switch to `ConfigEntry.runtime_data` [M]

**Why:** `runtime-data` Bronze rule. `hass.data` is for cross-entry or global state;
per-entry data belongs in `entry.runtime_data`.

**Files to touch:** `__init__.py`, `sensor.py`, `binary_sensor.py`, `calendar.py`,
`event.py`, `camera.py`, `statistics.py`, `trip_sensor.py`

**Pattern:**

```python
# __init__.py async_setup_entry — store
entry.runtime_data = coordinator           # replaces hass.data[DOMAIN][coordinator_key]

# Every platform's async_setup_entry — retrieve
coordinator = entry.runtime_data

# async_unload_entry — no manual cleanup needed;
# runtime_data is cleared automatically when the entry is unloaded
```

Remove the `coordinator_key` pattern everywhere. Delete lines that do
`hass.data[DOMAIN][coordinator_key] = coordinator` and the corresponding
`.get(coordinator_key)` reads.

The `hass.data[DOMAIN]` dict can remain for any truly global state (e.g., the
temp stop results during config flow — but see Task 9 for a better fix there).

**Type annotation for the entry (add to `__init__.py`):**
```python
type OpenPublicTransportConfigEntry = ConfigEntry[PublicTransportDataUpdateCoordinator]
```

---

### TASK 5 — Use `async_config_entry_first_refresh()` [S]

**Why:** `test-before-setup` Bronze rule. A failed first fetch should put the
entry into a retrying state, not silently succeed with `unavailable` state.

**File:** `__init__.py:220`, `trip_sensor.py`

```python
# Before
await coordinator.async_refresh()

# After
await coordinator.async_config_entry_first_refresh()
# This raises ConfigEntryNotReady on failure → HA retries automatically
```

**Special case — OTP startup latency:** The existing comment (lines 217–219)
notes that OTP instances take time to load their routing graph. Handle this by
catching `ConfigEntryNotReady` at a higher level or by using a longer
`async_config_entry_first_refresh` timeout, not by silently swallowing errors.
An alternative: add a config-level option for "skip first-fetch validation" for
self-hosted OTP instances. Document it clearly.

---

### TASK 6 — Implement `has-entity-name` across all platforms [M]

**Why:** `has-entity-name` Bronze rule. Entity names must compose from
device name + entity-specific suffix, not be hardcoded concatenations.

**What to do for each entity class:**

1. Add `_attr_has_entity_name = True`
2. Change `_attr_name` to be just the entity-specific suffix (a short noun)
3. Make sure `DeviceInfo.name` carries the stop/station identity

**Current (wrong):**
```python
# binary_sensor.py:77
self._attr_name = f"{provider.upper()} {place_dm} - {name_dm} Delays"
```

**Target:**
```python
# binary_sensor.py
_attr_has_entity_name = True

def __init__(self, ...):
    ...
    self._attr_name = "Delays"          # suffix only
    self._attr_device_info = DeviceInfo(
        identifiers={(DOMAIN, station_key)},
        name=f"{provider.upper()} {place_dm} – {name_dm}",   # full name on device
        ...
    )
```

**Entity suffix naming guide:**

| Class | `_attr_name` |
|---|---|
| `MultiProviderSensor` (main sensor) | `None` — the device name IS the entity |
| `PunctualitySensor` | `"Punctuality"` |
| `PublicTransportDelayBinarySensor` | `"Delays"` |
| Calendar | `"Schedule"` |
| Event | `"Disruptions"` |
| Camera | `"Board"` |
| `MultiStopSensor` | `None` or `"Departures"` |

When `_attr_name = None`, the entity inherits the device name — correct for the
primary/main entity per device.

**Also update `strings.json`** — add `entity:` block with entity name translations
if names are user-visible strings rather than hardcoded.

---

### TASK 7 — Fix config flow temp-stop storage [S]

**Why:** `common-modules` rule. `hass.data[f"{DOMAIN}_temp_stops"]` used as
temp storage during config flow (`config_flow.py:507, 516, 542, 546, 554, 557`)
leaks across concurrent flows and is an HA anti-pattern.

**Fix:** Store search results as instance variables on the flow object.

```python
# Before (config_flow.py)
self.hass.data[f"{DOMAIN}_temp_stops"] = stops
...
stops = self.hass.data.get(f"{DOMAIN}_temp_stops", [])

# After — in __init__ of OpenPublicTransportConfigFlow:
self._found_stops: list[dict] = []

# In async_step_stop_search:
self._found_stops = stops

# In async_step_stop_select:
stops = self._found_stops
```

Also fix the German strings in `_PROVIDER_CREDENTIAL_NAMES` (`__init__.py:83–91`):
```python
# Before
PROVIDER_OTP_CUSTOM: "OTP2 Eigene Instanz",
PROVIDER_VBN_OTP:    "VBN (Bremen/Niedersachsen) — OTP",

# After (English for HA Core)
PROVIDER_OTP_CUSTOM: "OTP2 Custom Instance",
PROVIDER_VBN_OTP:    "VBN (Bremen/Lower Saxony) — OTP",
```

---

### TASK 8 — Expand config flow test coverage [M]

**Why:** `config-flow-test-coverage` Bronze rule. Current tests only cover the
VRR happy path with a single stop result.

**Missing test cases to add in `tests/test_config_flow.py`:**

```
test_stop_select_step_multiple_results
    - search returns >1 stop → stop_select form shown
    - user selects one → proceeds to settings

test_stop_select_search_again
    - user selects "__search_again__" → back to stop_search

test_duplicate_entry_abort
    - same provider + station_id → async_abort with reason "already_configured"

test_options_flow
    - existing entry → init options flow → change departures/scan_interval
    - verify entry.options updated

test_api_key_providers
    - RMV flow: user → stop_search → api_key step → settings → entry created
    - Trafiklab: same
    - NTA: same (2-key flow)
    - VBN OTP: same

test_otp_custom_url_flow
    - user → otp_custom_url step → stop_search → settings

test_trip_flow_happy_path
    - user selects "trip" type → origin search → destination search → settings

test_multi_stop_flow
    - user selects "multi_stop" → entity picker → entry created

test_stop_search_no_results
    - _search_stops returns [] → error "no_results" shown

test_stop_search_api_error
    - _search_stops raises exception → error "api_error" shown

test_nta_manual_id_flow
    - NTA path that skips stop search and accepts manual station ID
```

Mock `_search_stops` via `unittest.mock.patch` on the method directly (not the
provider) so individual providers don't need to be stubbed.

---

### TASK 9 — Verify `entity-event-setup` in `multi_stop.py` [S]

**Why:** State change listeners must be unsubscribed when the entity is removed.

**Check in `multi_stop.py` `MultiStopSensor`:**
```python
async def async_added_to_hass(self) -> None:
    await super().async_added_to_hass()
    # Every async_track_* call returns an unsubscribe callback.
    # It MUST be passed to self.async_on_remove:
    self.async_on_remove(
        async_track_state_change_event(
            self.hass, self._source_entities, self._handle_state_change
        )
    )
```

If it already does this, mark as done. If `async_on_remove` is missing, add it.

---

### TASK 10 — Submit brands PR [S]

**Why:** `brands` rule requires a separate PR to `home-assistant/brands`.

**Steps:**
1. Fork `home-assistant/brands`
2. Create `custom_integrations/openpublictransport/` (or `integrations/openpublictransport/`)
   with `icon.png` and `logo.png` from the current `brand/` folder
3. Open PR — it typically takes 1–2 weeks to merge
4. This can be done in parallel with any other task

---

### TASK 11 — Write HA Core documentation PR [M]

**Why:** `docs-high-level-description`, `docs-installation-instructions`,
`docs-removal-instructions` all require a page on `home-assistant.io`.

**Required sections in the docs page:**
- High-level description (what the integration does, supported providers)
- Prerequisites (API keys, which providers need them)
- Installation via config flow (step-by-step with screenshots)
- Available entities (sensor, binary sensor, calendar, event, camera, statistics)
- Actions reference (refresh, plan_trip, check_delays, announce_departure)
- Options / reconfiguration
- Removal instructions
- Troubleshooting (rate limits, OTP startup delay)

Open a PR to `home-assistant/home-assistant.io` in parallel with the code work.

---

### TASK 12 — Add `test-before-configure` for NTA and custom-URL providers [S]

**Why:** For providers that skip stop search (NTA accepts manual ID, OTP Custom
accepts a URL), no API connectivity check happens before the entry is created.

**For NTA:** After the user enters the station ID, make a minimal GTFS-RT request
and show an error if it fails:
```python
# In the NTA-specific flow step, before async_create_entry:
try:
    result = await self._test_nta_connection(api_key, station_id)
except Exception:
    errors["base"] = "cannot_connect"
    return self.async_show_form(...)
```

**For OTP Custom:** After the URL step, attempt a `/otp/routers/default/index`
health-check request and validate the response before proceeding to stop search.

---

## Bronze Quality Scale Checklist

| Rule | Status | Task |
|---|---|---|
| action-setup | ⚠️ Partial | Task 2 |
| appropriate-polling | ✅ Done | — |
| brands | ❌ Missing | Task 10 |
| common-modules | ⚠️ Partial | Task 7 |
| config-flow-test-coverage | ⚠️ Partial | Task 8 |
| config-flow | ✅ Done | — |
| dependency-transparency | ❌ Missing | Task 3 |
| docs-actions | ✅ Done | — |
| docs-high-level-description | ⚠️ Needs HA docs PR | Task 11 |
| docs-installation-instructions | ⚠️ Needs HA docs PR | Task 11 |
| docs-removal-instructions | ⚠️ Needs HA docs PR | Task 11 |
| entity-event-setup | ⚠️ Verify | Task 9 |
| entity-unique-id | ✅ Done | — |
| has-entity-name | ❌ Missing | Task 6 |
| runtime-data | ❌ Missing | Task 4 |
| test-before-configure | ⚠️ Partial | Task 12 |
| test-before-setup | ❌ Missing | Task 5 |
| unique-config-entry | ✅ Done | — |

---

## Key Constraints / Do Not Break

- **All 28 providers must keep working** — never remove a provider or change its
  `provider_id` constant; existing config entries depend on these strings.
- **Application Credentials integration** — API keys must stay in the AC store
  (`application_credentials.py`), not revert to `config_entry.data`.
- **Migration path** — `_async_migrate_credential` in `__init__.py:94` must keep
  running on startup to migrate keys from old entries; do not remove it.
- **Unique IDs are stable** — `f"{provider}_{station_id}"` is the unique_id
  pattern. Do not change the format — existing users' entity registries depend on it.
- **`services.yaml` must stay in sync** with service schemas in `__init__.py`.
- **Translation keys must stay in sync** between `strings.json` and every file
  in `translations/`. Adding a new key in `strings.json` requires adding it to
  `translations/en.json` at minimum.

---

## Recommended Execution Order

```
Task 1 (pytz)             → no dependencies, do first
Task 2 (action-setup)     → no dependencies, easy win
Task 3 (PyPI lib)         → critical path; everything else is easier after this
Task 4 (runtime_data)     → can start after Task 3 integration side is clear
Task 5 (first_refresh)    → 2-line change, do after Task 4
Task 6 (has_entity_name)  → do after Task 4 (uses runtime_data pattern)
Task 7 (flow cleanup)     → independent, any time
Task 8 (tests)            → can do incrementally throughout; prioritise options flow
Task 9 (multi_stop check) → quick verify, any time
Tasks 10, 11, 12          → external work, do in parallel with code tasks
```

Tasks 1, 2, 7, 9 are fully independent and can be batched into one PR.
Tasks 3 → 4 → 5 → 6 form the main sequence and should be a coordinated
effort (ideally a single large PR or a short series of stacked PRs).
