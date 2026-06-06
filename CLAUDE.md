# CLAUDE.md — OpenPublicTransport HA Core Submission

## Project Goal

Prepare the custom integration `openpublictransport` for submission to
**Home Assistant Core** (`home-assistant/core`).

**Current status: Bronze Quality Scale achieved ✅**

Next milestone: Silver Quality Scale.

---

## Repository Layout

```
custom_components/openpublictransport/
├── __init__.py            Entry setup, 4 services, credential migration
├── manifest.json          Domain metadata and pip requirements
├── quality_scale.yaml     HA Quality Scale compliance tracking
├── const.py               All constants, provider IDs, API URLs
├── config_flow.py         ConfigFlow + OptionsFlow + NTA stop ID step
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
├── brand/                 icon.png + logo.png (served by HA 2026.3+)
└── providers/
    ├── __init__.py        get_provider(session, ...) factory + register_provider()
    ├── base.py            BaseProvider ABC — takes aiohttp.ClientSession, no HA dep
    ├── efa_base.py        EFA/XML base → VRR KVV HVV MVV VVS VGN VAG VRN VVO
    ├── trias_base.py      TRIAS/SOAP base → RMV NWL NVBW
    ├── otp_base.py        OTP2 REST/GraphQL base → OPT VBN OTP_CUSTOM
    ├── fptf_base.py       FPTF REST base → Transitous
    └── [24 concrete provider modules]

tests/
├── conftest.py
├── test_init.py
├── test_config_flow.py    (96 tests — full Bronze coverage)
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
`tests/conftest.py`. The `auto_enable_custom_integrations` autouse fixture is required.

Minimum HA version: `2026.3.0` (declared in `hacs.json`).
Test matrix: Python 3.13, 3.14.

---

## Architecture Notes

### Data flow
```
ConfigEntry.data / options
  └── PublicTransportDataUpdateCoordinator (sensor.py)
        ├── _ensure_provider() → get_provider(provider_id, session, ...)
        │     session = async_get_clientsession(hass)  [lazy, first fetch only]
        ├── _async_update_data() → _fetch_departures() → provider.fetch_departures()
        └── CoordinatorEntity subclasses (sensor, binary_sensor, calendar,
                                          event, camera, statistics)
```

### Provider seam — HA coupling removed (Task 3 ✅)
All providers in `providers/` receive `session: aiohttp.ClientSession` — no HA imports.
Session is injected at the integration boundary in `sensor.py:_ensure_provider()`.
Providers are published as a standalone PyPI library: `python-openpublictransport`.

### Runtime storage (Task 4 ✅)
```python
# __init__.py async_setup_entry
entry.runtime_data = coordinator

# Every platform async_setup_entry
coordinator = config_entry.runtime_data
```

### Service registration (Task 2 ✅)
All 4 service handlers live in `async_setup` — registered once per HA start, not per entry.

---

## quality_scale.yaml — Format & Valid Values

Tracked in `custom_components/openpublictransport/quality_scale.yaml`.
Rule names in the YAML use **snake_case**; HA docs and this file use **kebab-case** for readability.

```yaml
rules:
  config_flow: done                         # rule is implemented
  docs_high_level_description:
    status: exempt                          # rule does not apply
    comment: Reason why it is exempt
  reauthentication_flow:
    status: todo                            # rule not yet implemented
    comment: Optional note on plans
```

Valid status values: `done` | `exempt` (comment required) | `todo`

---

## Bronze Quality Scale — COMPLETED ✅

All 18 tracked Bronze rules are done or exempt.
(HA docs list 19; one rule may have been added after this integration was validated.)

| Rule | Status | Notes |
|---|---|---|
| action-setup | ✅ Done | Registered in `async_setup` |
| appropriate-polling | ✅ Done | |
| brands | ✅ Done | `brand/` folder, HA 2026.3+ |
| common-modules | ✅ Done | |
| config-flow | ✅ Done | |
| config-flow-test-coverage | ✅ Done | 96 tests |
| dependency-transparency | ✅ Done | `python-openpublictransport` on PyPI |
| docs-actions | ✅ Done | |
| docs-high-level-description | ✅ Exempt | docs.openpublictransport.net |
| docs-installation-instructions | ✅ Exempt | docs.openpublictransport.net |
| docs-removal-instructions | ✅ Exempt | docs.openpublictransport.net |
| entity-event-setup | ✅ Done | |
| entity-unique-id | ✅ Done | |
| has-entity-name | ✅ Done | |
| runtime-data | ✅ Done | |
| test-before-configure | ✅ Done | |
| test-before-setup | ✅ Done | |
| unique-config-entry | ✅ Done | |

---

## Silver Quality Scale — Next Milestone

| Rule | Official description | Notes |
|---|---|---|
| action-exceptions | Service actions raise exceptions when encountering failures | |
| config-entry-unloading | Support config entry unloading | |
| docs-configuration-parameters | The documentation describes all integration configuration options | |
| docs-installation-parameters | The documentation describes all integration installation parameters | |
| entity-unavailable | Mark entity unavailable if appropriate | |
| integration-owner | Has an integration owner | |
| log-when-unavailable | If internet/device/service is unavailable, log once when unavailable and once when back | |
| parallel-updates | Number of parallel updates is specified | |
| reauthentication-flow | Reauthentication needs to be available via the UI | |
| test-coverage | Above 95% test coverage for all integration modules | Currently ~45% |

---

## Gold Quality Scale — Future

(HA docs list 24 Gold rules; 21 are identifiable from the rules index — 3 may be recently added.)

| Rule | Official description |
|---|---|
| devices | The integration creates devices |
| diagnostics | Implements diagnostics |
| discovery | Devices can be discovered |
| discovery-update-info | Integration uses discovery info to update network information |
| docs-data-update | The documentation describes how data is updated |
| docs-examples | The documentation provides automation examples the user can use |
| docs-known-limitations | The documentation describes known limitations of the integration |
| docs-supported-devices | The documentation describes known supported / unsupported devices |
| docs-supported-functions | The documentation describes the supported functionality |
| docs-troubleshooting | The documentation provides troubleshooting information |
| docs-use-cases | The documentation describes use cases to illustrate how this integration can be used |
| dynamic-devices | Devices added after integration setup |
| entity-category | Entities are assigned an appropriate EntityCategory |
| entity-device-class | Entities use device classes where possible |
| entity-disabled-by-default | Integration disables less popular (or noisy) entities |
| entity-translations | Entities have translated names |
| exception-translations | Exception messages are translatable |
| icon-translations | Entities implement icon translations |
| reconfiguration-flow | Integrations should have a reconfigure flow |
| repair-issues | Repair issues and repair flows are used when user intervention is needed |
| stale-devices | Stale devices are removed |

---

## Platinum Quality Scale — Future

| Rule | Official description |
|---|---|
| async-dependency | Dependency is async |
| inject-websession | The integration dependency supports passing in a websession |
| strict-typing | Strict typing |

---

## Key Constraints / Do Not Break

- **All 28 providers must keep working** — never remove a provider or change its
  `provider_id` constant; existing config entries depend on these strings.
- **Application Credentials integration** — API keys must stay in the AC store
  (`application_credentials.py`), not revert to `config_entry.data`.
- **Migration path** — `_async_migrate_credential` in `__init__.py` must keep
  running on startup to migrate keys from old entries; do not remove it.
- **Unique IDs are stable** — `f"{provider}_{station_id}"` is the unique_id
  pattern. Do not change the format — existing users' entity registries depend on it.
- **`services.yaml` must stay in sync** with service schemas in `__init__.py`.
- **Translation keys must stay in sync** between `strings.json` and every file
  in `translations/`. Adding a new key in `strings.json` requires adding it to
  `translations/en.json` at minimum.
- **Provider session is lazy** — `_ensure_provider()` in `sensor.py` only calls
  `async_get_clientsession()` on first actual data fetch, not in `__init__`.
