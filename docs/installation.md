# Installation

## Marketplace Installation (Recommended)

Since Home Assistant 2026.11, HACS is built into Home Assistant as the **Marketplace**.
It is the recommended installation method.

### Prerequisites

- Home Assistant 2026.3 or newer

### Steps

1. Open **Settings** > **Marketplace**
2. Search for **"OpenPublicTransport"** and click **Download**
3. Restart Home Assistant

!!! note "Home Assistant before 2026.11"
    Use [HACS](https://hacs.xyz/) instead: open HACS, go to **Integrations**, search for
    **"OpenPublicTransport"** and click **Download**. When you update to 2026.11, the
    Marketplace takes over the HACS install automatically, including updates.

!!! tip
    After installation, the integration will appear in your list of available integrations.

## Manual Installation

If you prefer not to use the Marketplace, you can install the integration manually.

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
3. Search for "OpenPublicTransport"

If the integration appears in the list, installation was successful.

## Updating

### Marketplace Updates

The Marketplace (or HACS on older versions) shows an update entity when a new release is out.
Click **Update** and restart Home Assistant; a repair reminds you of the restart.

### Manual Updates

1. Download the latest release
2. Replace all files in `custom_components/openpublictransport/`
3. Restart Home Assistant

!!! warning
    Always backup your configuration before updating.
