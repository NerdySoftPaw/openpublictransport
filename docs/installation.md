# Installation

## HACS Installation (Recommended)

[HACS](https://hacs.xyz/) (Home Assistant Community Store) is the recommended installation method.

### Prerequisites

- Home Assistant 2024.1 or newer
- HACS installed and configured

### Steps

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the three dots in the top right and select **Custom repositories**
4. Add this repository URL: `https://github.com/NerdySoftPaw/openpublictransport`
5. Select **Integration** as category
6. Click **Add**
7. Search for "Public" and install the integration
8. Restart Home Assistant

!!! tip
    After installation, the integration will appear in your list of available integrations.

## Manual Installation

If you prefer not to use HACS, you can install the integration manually.

### Steps

1. Download the latest release from [GitHub Releases](https://github.com/NerdySoftPaw/openpublictransport/releases)
2. Extract the `custom_components/openpublictransport` folder
3. Copy the folder to your Home Assistant `custom_components` directory:
   ```
   <config>/custom_components/openpublictransport/
   ```
4. Restart Home Assistant

### Directory Structure

After installation, your directory should look like this:

```
custom_components/
└── openpublictransport/
    ├── __init__.py
    ├── binary_sensor.py
    ├── config_flow.py
    ├── const.py
    ├── manifest.json
    ├── sensor.py
    ├── services.yaml
    ├── strings.json
    └── providers/
        ├── __init__.py
        ├── base.py
        ├── hvv.py
        ├── kvv.py
        ├── nta.py
        ├── trafiklab.py
        └── vrr.py
```

## Verify Installation

After restarting Home Assistant:

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Public Transport Departures"

If the integration appears in the list, installation was successful.

## Updating

### HACS Updates

HACS will notify you when updates are available. Simply click **Update** and restart Home Assistant.

### Manual Updates

1. Download the latest release
2. Replace all files in `custom_components/openpublictransport/`
3. Restart Home Assistant

!!! warning
    Always backup your configuration before updating.
