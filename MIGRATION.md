# Migration Guide

## Migration: `vrr` to `openpublictransport` (Latest)

> **Note:** This section applies when upgrading from versions that used the `vrr` domain to the new `openpublictransport` domain.
> If you're installing fresh, you can skip this guide entirely.

### What Changed

| | Old | New |
|--|-----|-----|
| **Repository** | `NerdySoftPaw/hacs-publictransport` | `NerdySoftPaw/openpublictransport` |
| **Domain** | `vrr` | `openpublictransport` |
| **Entity IDs** | `sensor.vrr_*` | `sensor.openpublictransport_*` |
| **Services** | `vrr.refresh_departures` | `openpublictransport.refresh_departures` |
| **Component folder** | `custom_components/vrr/` | `custom_components/openpublictransport/` |

### Migration Steps

#### Step 1: Update HACS Repository

1. Open **HACS** > **Integrations**
2. Remove the old `hacs-publictransport` custom repository
3. Add the new repository URL:
   ```
   https://github.com/NerdySoftPaw/openpublictransport
   ```
4. Select type: **Integration**
5. Click **ADD** and download the integration

#### Step 2: Update the Component Folder

1. Remove the old folder: `custom_components/vrr/`
2. The new integration will be installed to: `custom_components/openpublictransport/`

#### Step 3: Update Dashboards

Update all entity references in your Lovelace dashboards:

- `sensor.vrr_*` becomes `sensor.openpublictransport_*`

For example:
```yaml
# Old
entity: sensor.vrr_dusseldorf_hauptbahnhof

# New
entity: sensor.openpublictransport_dusseldorf_hauptbahnhof
```

#### Step 4: Update Automations

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

#### Step 5: Update Debug Logging (if configured)

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

#### Step 6: Restart Home Assistant

1. Go to **Settings** > **System** > **Restart**
2. Wait for Home Assistant to restart
3. Verify your sensors are working under the new entity IDs

---

## Migration: `VRRAPI-HACS` to `hacs-publictransport` (Legacy)

> **Note:** This section is only relevant when upgrading from version `2026.01.22` or earlier to version `2026.01.23` and higher.
> If you migrated previously, you can skip this section.

### Repository Change

The integration moved from the original repository:

| | Old | New |
|--|-----|-----|
| **Repository** | `NerdySoftPaw/VRRAPI-HACS` | `NerdySoftPaw/openpublictransport` |
| **Providers** | VRR only | VRR, KVV, HVV, Trafiklab, NTA |
| **Status** | ⚠️ Deprecated | ✅ Active Development |

---

## Migration Steps

Your existing configuration will be **automatically migrated**. Just follow these simple steps:

### Step 1: Add the New Repository

1. Open **HACS** → **Integrations**
2. Click the three dots (⋮) in the top right corner
3. Select **Custom repositories**
4. Add the URL:
   ```
   https://github.com/NerdySoftPaw/openpublictransport
   ```
5. Select type: **Integration**
6. Click **ADD**

### Step 2: Download the New Version

1. Search for "Public Transport" in HACS
2. Click on **Public Transport Departures**
3. Click **Download**

### Step 3: Remove the Old Repository (Optional)

1. In HACS, find the old "VRR" entry from VRRAPI-HACS
2. Click the three dots (⋮) > **Remove**

### Step 4: Restart Home Assistant

1. Go to **Settings** → **System** → **Restart**
2. Wait for Home Assistant to restart

### Step 5: Done! ✅

Your existing sensors, configuration, and historical data are automatically preserved.

---

## What Gets Migrated

| Item | Status |
|------|--------|
| Sensor configuration | ✅ Preserved |
| Entity IDs | ✅ Unchanged |
| Historical data | ✅ Preserved |
| Automations using VRR entities | ✅ Continue working |
| Dashboard cards | ✅ Continue working |

---

## New Features After Migration

After migrating to version `2026.01.23` or higher, you'll have access to:

- 🇮🇪 **NTA Ireland** - New provider for Irish public transport
- 🧠 **Fuzzy Search** - Find stops even with typos
- ⚡ **Better Performance** - 20-30% faster updates
- 📦 **API Caching** - Reduced API calls

---

## Troubleshooting

### Integration not showing after restart?

1. Check if the custom component folder exists: `/config/custom_components/openpublictransport/`
2. Check Home Assistant logs for errors
3. Try clearing browser cache and refreshing

### HACS shows old version?

1. Make sure you added the new repository URL
2. Remove the old VRRAPI-HACS entry from HACS
3. Download from the new openpublictransport repository

### Need Help?

- 📖 [Documentation](https://docs.openpublictransport.net/)
- 🐛 [Report an Issue](https://github.com/NerdySoftPaw/openpublictransport/issues)
