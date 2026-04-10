# Migration Guide

There have been two major migrations in the project's history. Follow the section that applies to you.

---

## Migration 2: `hacs-publictransport` → `openpublictransport` (v2026.04.08)

!!! danger "Breaking Change — Domain Renamed"
    Version `2026.04.08` renames the integration domain from `vrr` to `openpublictransport`.
    All entity IDs, services, and the component folder change. **Existing users must re-configure.**

This migration applies if you were using the `hacs-publictransport` repository with the `vrr` domain.

### What Changed

| | Before | After |
|--|--------|-------|
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

Delete the old component folder:

```
custom_components/vrr/
```

#### Step 3: Install the New Version

1. Open **HACS** > **Integrations**
2. Add custom repository: `https://github.com/NerdySoftPaw/openpublictransport`
3. Install the **openpublictransport** integration
4. Restart Home Assistant

#### Step 4: Re-configure Your Stops

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for **Public Transport Departures**
4. Follow the setup wizard to add your stops again

#### Step 5: Update Dashboards & Automations

Update all entity references in your Lovelace dashboards and automations:

```yaml
# Old
entity: sensor.vrr_dusseldorf_hauptbahnhof
service: vrr.refresh_departures

# New
entity: sensor.openpublictransport_dusseldorf_hauptbahnhof
service: openpublictransport.refresh_departures
```

#### Step 6: Update Debug Logging (if configured)

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

#### Step 7: Restart Home Assistant

1. Go to **Settings** > **System** > **Restart**
2. Verify your sensors are working under the new entity IDs

!!! tip "Entity History"
    Entity history from `sensor.vrr_*` entities will not carry over to `sensor.openpublictransport_*` entities. This is a limitation of Home Assistant when entity IDs change.

---

## Migration 1: `VRRAPI-HACS` → `hacs-publictransport` (Legacy)

!!! note "No Breaking Change"
    This migration only changed the **repository name** — the domain stayed `vrr`, so no entity IDs or services changed. Your configuration was automatically preserved.

This applies if you were using the original `VRRAPI-HACS` repository.

### What Changed

| | Before | After |
|--|--------|-------|
| **Repository** | `NerdySoftPaw/VRRAPI-HACS` | `NerdySoftPaw/hacs-publictransport` |
| **Domain** | `vrr` (unchanged) | `vrr` (unchanged) |
| **Entity IDs** | `sensor.vrr_*` (unchanged) | `sensor.vrr_*` (unchanged) |
| **Providers** | VRR only | Multi-provider (VRR, KVV, HVV, and more) |

### Steps

1. Open **HACS** > **Integrations**
2. Remove the old VRRAPI-HACS entry
3. Add the new repository: `https://github.com/NerdySoftPaw/hacs-publictransport`
4. Download the integration
5. Restart Home Assistant

Your existing configuration was automatically preserved — no re-configuration needed.

!!! warning "Now Continue With Migration 2"
    The `hacs-publictransport` repository has since been renamed to `openpublictransport` with a domain change. Follow **Migration 2** above to complete the update to the current version.

---

## Troubleshooting

### Integration not showing after restart?

1. Check if the custom component folder exists: `/config/custom_components/openpublictransport/`
2. Make sure the old `custom_components/vrr/` folder is deleted
3. Check Home Assistant logs for errors
4. Try clearing browser cache and refreshing

### HACS shows old version?

1. Remove any old VRRAPI-HACS or hacs-publictransport entries from HACS
2. Add the new repository: `https://github.com/NerdySoftPaw/openpublictransport`
3. Download from the new openpublictransport repository

### Need Help?

- [Documentation](https://docs.openpublictransport.net/)
- [Report an Issue](https://github.com/NerdySoftPaw/openpublictransport/issues)
- [GitHub Discussions](https://github.com/NerdySoftPaw/openpublictransport/discussions)
