# Migration Guide

!!! warning "Version Note"
    This migration guide is **only relevant** when upgrading from version `2026.01.22` or earlier to version `2026.01.23` and higher.
    
    If you're installing fresh, you can skip this guide entirely and go to [Installation](installation.md).

## Repository Change

The integration has moved to a new repository with expanded multi-provider support:

| | Old | New |
|--|-----|-----|
| **Repository** | `NerdySoftPaw/VRRAPI-HACS` | `NerdySoftPaw/openpublictransport` |
| **Providers** | VRR only | VRR, KVV, HVV, Trafiklab, NTA |
| **Status** | :material-alert: Deprecated | :material-check-circle: Active Development |

---

## Migration Steps

Your existing configuration will be **automatically migrated**. Just follow these simple steps:

### Step 1: Add the New Repository

1. Open **HACS** → **Integrations**
2. Click the three dots (:material-dots-vertical:) in the top right corner
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
2. Click the three dots (:material-dots-vertical:) → **Remove**

### Step 4: Restart Home Assistant

1. Go to **Settings** → **System** → **Restart**
2. Wait for Home Assistant to restart

### Step 5: Done! :material-check:

Your existing sensors, configuration, and historical data are automatically preserved.

---

## What Gets Migrated

| Item | Status |
|------|--------|
| Sensor configuration | :material-check: Preserved |
| Entity IDs | :material-check: Unchanged |
| Historical data | :material-check: Preserved |
| Automations using VRR entities | :material-check: Continue working |
| Dashboard cards | :material-check: Continue working |

---

## New Features After Migration

After migrating to version `2026.01.23` or higher, you'll have access to:

- :flag_ie: **NTA Ireland** - New provider for Irish public transport
- :brain: **Fuzzy Search** - Find stops even with typos
- :zap: **Better Performance** - 20-30% faster updates
- :package: **API Caching** - Reduced API calls

See the full [Release Notes](https://github.com/NerdySoftPaw/openpublictransport/blob/main/RELEASE_NOTES.md) for details.

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

- :material-bug: [Report an Issue](https://github.com/NerdySoftPaw/openpublictransport/issues)
- :material-forum: [GitHub Discussions](https://github.com/NerdySoftPaw/openpublictransport/discussions)
