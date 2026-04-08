# Migration Guide

## Migration: `vrr` → `openpublictransport` (v2026.04.08)

> **⚠️ BREAKING CHANGE** — Version `2026.04.08` renames the integration from `vrr` to `openpublictransport`.
> All entity IDs, services, and the component folder change. Existing users must re-configure.

### What Changed

| | Old | New |
|--|-----|-----|
| **Repository** | `NerdySoftPaw/hacs-publictransport` | `NerdySoftPaw/openpublictransport` |
| **Domain** | `vrr` | `openpublictransport` |
| **Entity IDs** | `sensor.vrr_*` | `sensor.openpublictransport_*` |
| **Binary Sensors** | `binary_sensor.vrr_*` | `binary_sensor.openpublictransport_*` |
| **Services** | `vrr.refresh_departures` | `openpublictransport.refresh_departures` |
| **Component folder** | `custom_components/vrr/` | `custom_components/openpublictransport/` |

### Migration Steps

#### Step 1: Remove the Old Integration

1. Go to **Settings** > **Devices & Services**
2. Find the old **VRR** / **Public Transport Departures** integration
3. Delete all config entries
4. If installed via HACS: remove the old repository from HACS

#### Step 2: Remove Old Files

Delete the old component folder: `custom_components/vrr/`

#### Step 3: Install the New Version

1. Open **HACS** > **Integrations**
2. Search for **Public Transport Departures**
3. Install the `openpublictransport` integration
4. Restart Home Assistant

#### Step 4: Re-configure Your Stops

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for **Public Transport Departures**
4. Follow the setup wizard to add your stops again

#### Step 5: Update Dashboards

Update all entity references in your Lovelace dashboards:

```yaml
# Old
entity: sensor.vrr_dusseldorf_hauptbahnhof

# New
entity: sensor.openpublictransport_dusseldorf_hauptbahnhof
```

```yaml
# Old
entity: binary_sensor.vrr_dusseldorf_hauptbahnhof_delays

# New
entity: binary_sensor.openpublictransport_dusseldorf_hauptbahnhof_delays
```

#### Step 6: Update Automations

```yaml
# Old
service: vrr.refresh_departures
data:
  entity_id: sensor.vrr_dusseldorf_hauptbahnhof

# New
service: openpublictransport.refresh_departures
data:
  entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
```

#### Step 7: Update Debug Logging (if configured)

```yaml
# Old
logger:
  logs:
    custom_components.vrr: debug

# New
logger:
  logs:
    custom_components.openpublictransport: debug
```

#### Step 8: Restart Home Assistant

1. Go to **Settings** > **System** > **Restart**
2. Verify your sensors are working under the new entity IDs

> **Note:** Entity history from the old `sensor.vrr_*` entities will not carry over. This is a limitation of Home Assistant when entity IDs change.

---

## Migration: `VRRAPI-HACS` → `openpublictransport` (Legacy)

> **Note:** This section is only relevant if upgrading from the original `VRRAPI-HACS` repository (version `2026.01.22` or earlier).

| | Old | New |
|--|-----|-----|
| **Repository** | `NerdySoftPaw/VRRAPI-HACS` | `NerdySoftPaw/openpublictransport` |
| **Providers** | VRR only | VRR, KVV, HVV, Trafiklab, NTA |
| **Status** | ⚠️ Deprecated | ✅ Active Development |

### Steps

1. Remove the old VRRAPI-HACS entry from HACS
2. Add the new repository: `https://github.com/NerdySoftPaw/openpublictransport`
3. Download the integration
4. Restart Home Assistant
5. Then follow the **vrr → openpublictransport** migration above

---

## Need Help?

- 📖 [Documentation](https://docs.openpublictransport.net/)
- 🐛 [Report an Issue](https://github.com/NerdySoftPaw/openpublictransport/issues)
