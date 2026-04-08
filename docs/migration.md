# Migration Guide

## Migration: `vrr` → `openpublictransport` (v2026.04.08)

!!! danger "Breaking Change"
    Version `2026.04.08` renames the integration from `vrr` to `openpublictransport`.
    All entity IDs, services, and the component folder change. **Existing users must re-configure.**

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

1. Go to **Settings** → **Devices & Services**
2. Find the old **VRR** / **Public Transport Departures** integration
3. Delete all config entries
4. If installed via HACS: remove the old repository from HACS

#### Step 2: Remove Old Files

Delete the old component folder:

```
custom_components/vrr/
```

#### Step 3: Install the New Version

1. Open **HACS** → **Integrations**
2. Search for **Public Transport Departures**
3. Install the `openpublictransport` integration
4. Restart Home Assistant

#### Step 4: Re-configure Your Stops

1. Go to **Settings** → **Devices & Services**
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

Update all automations that reference old entity IDs or services:

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

1. Go to **Settings** → **System** → **Restart**
2. Wait for Home Assistant to restart
3. Verify your sensors are working under the new entity IDs

!!! tip "Entity History"
    Entity history from the old `sensor.vrr_*` entities will not carry over to the new `sensor.openpublictransport_*` entities. This is a limitation of Home Assistant when entity IDs change.

---

## Migration: `VRRAPI-HACS` → `hacs-publictransport` (Legacy)

!!! note "Legacy Migration"
    This section is only relevant if you are upgrading from the original `VRRAPI-HACS` repository (version `2026.01.22` or earlier).
    If you already migrated previously, skip this and follow the `vrr` → `openpublictransport` migration above.

### Repository Change

| | Old | New |
|--|-----|-----|
| **Repository** | `NerdySoftPaw/VRRAPI-HACS` | `NerdySoftPaw/openpublictransport` |
| **Providers** | VRR only | VRR, KVV, HVV, Trafiklab, NTA |
| **Status** | :material-alert: Deprecated | :material-check-circle: Active Development |

### Steps

1. Open **HACS** → **Integrations**
2. Remove the old VRRAPI-HACS entry
3. Add the new repository: `https://github.com/NerdySoftPaw/openpublictransport`
4. Download the integration
5. Restart Home Assistant

Your existing configuration was automatically migrated in this step. However, with version `2026.04.08` the domain changed — follow the `vrr` → `openpublictransport` migration above to complete the update.

---

## Troubleshooting

### Integration not showing after restart?

1. Check if the custom component folder exists: `/config/custom_components/openpublictransport/`
2. Check Home Assistant logs for errors
3. Try clearing browser cache and refreshing

### HACS shows old version?

1. Make sure you added the new repository URL
2. Remove any old VRRAPI-HACS or hacs-publictransport entries from HACS
3. Download from the new openpublictransport repository

### Need Help?

- :material-book-open-variant: [Documentation](https://docs.openpublictransport.net/)
- :material-bug: [Report an Issue](https://github.com/NerdySoftPaw/openpublictransport/issues)
- :material-forum: [GitHub Discussions](https://github.com/NerdySoftPaw/openpublictransport/discussions)
