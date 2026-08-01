# Configuration

The integration uses an intuitive multi-step setup wizard with autocomplete functionality.

## Setup Wizard

When you add the integration, you'll first see a confirmation dialog:

![Confirm setup](assets/screenshots/config-flow/01-confirm-dialog.png)

Click **OK** to start the setup wizard.

### Step 1: Select Provider

Choose your transit provider from the descriptive dropdown. Each entry shows the provider's full name and region (e.g. "VRR — Rhein-Ruhr (NRW)" instead of just "vrr"). You can also select the entry type: **Departure Monitor**, **Trip Planner**, or **Multi-Stop**.

![Provider selection](assets/screenshots/config-flow/02-provider-selection.png)

All 28 providers are available — see the [full provider list](providers/index.md) for details.

!!! note
    Most providers require no API key. Trafiklab (Sweden), NTA (Ireland), and RMV (Frankfurt) require a free API key — you'll be prompted to enter it in the next step.

### Step 2: API Key (if required)

For **Trafiklab** and **NTA** providers, you'll need to enter your API key.

See the provider-specific documentation for instructions:

- [Trafiklab API Key](providers/trafiklab.md#api-key)
- [NTA API Key](providers/nta.md#api-key)

### Step 3: Search for Stop

Enter your stop/station name. The integration will search and suggest matching stops.

![Stop search](assets/screenshots/config-flow/04-stop-search-filled.png)

**Tips for better search results:**

- Use the "Stop, City" format for precise results (e.g. "Holthausen, Düsseldorf") — the integration splits this into a stop name and city filter automatically
- You can also enter the city name along with the stop name (e.g., "Düsseldorf Hauptbahnhof")
- The search is **case-insensitive** — "karlsruhe hauptbahnhof" works just as well as "Karlsruhe Hauptbahnhof"
- For OTP providers (openpublictransport.net, custom OTP2): you can also enter an address or place of interest (e.g. "KIT Karlsruhe") — the integration geocodes it and finds nearby stops automatically
- The search handles typos and umlaut variations automatically
- For Swedish/Irish stops, use local naming conventions

### Step 4: Select Stop

If multiple stops match your search, you'll be presented with a list to choose from. Each entry shows:

- Stop name
- City/place (in parentheses)

### Step 5: Configure Settings

![Settings](assets/screenshots/config-flow/05-settings.png)

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| **Number of departures** | 10 | 1-20 | How many departures to fetch |
| **Transportation types** | All | Multi-select | Filter by transport type |
| **Scan interval** | 60 | 10-3600 seconds | How often to update |
| **Use provider logo** | Off | On/Off | Show provider logo instead of transport icon |

After completing the settings, the integration will create a device with all entities:

![Success](assets/screenshots/config-flow/06-success.png)

The integration will now appear on your Integrations page:

![Integrations page](assets/screenshots/config-flow/13-integrations-configured.png)

## Adding Multiple Stops

To monitor multiple stops:

1. Go to **Settings** > **Devices & Services**
2. Find the "Public Transport Departures" integration
3. Click **Add Entry**
4. Follow the setup wizard again

Each stop will create its own sensor and binary sensor entities.

## Modifying Settings

After initial setup, you can modify settings:

1. Go to **Settings** > **Devices & Services**
2. Find your stop entry
3. Click **Configure**
4. Adjust settings as needed

!!! tip
    You can change:

    - Number of departures
    - Transportation type filter
    - Scan interval
    - Provider logo display

## Configuration Options Reference

### Number of Departures

Controls how many upcoming departures are fetched from the API.

- **Minimum**: 1
- **Maximum**: 20
- **Recommended**: 5-10

Higher values provide more information but increase API usage.

### Transportation Types

Filter departures by transport type:

| Type | Description |
|------|-------------|
| `train` | All trains (ICE, IC, RE, RB) |
| `subway` | Subway/Metro (U-Bahn) |
| `tram` | Tram/Streetcar |
| `bus` | All bus types |
| `ferry` | Ferry services |
| `taxi` | Taxi/On-demand |

### Scan Interval

How often the integration fetches new data from the API.

- **Minimum**: 10 seconds
- **Maximum**: 3600 seconds (1 hour)
- **Recommended**: 60-120 seconds

!!! warning
    Setting very low intervals may trigger rate limiting on some providers.

### Use Provider Logo

When enabled, the entity picture shows the provider's logo instead of the dynamic transport type icon.

### Departure Filters

Three optional filters narrow the departure list. All are comma-separated, all are applied
after the data is fetched, and leaving one empty disables it. When any filter is active the
integration fetches a larger raw board so filtered results aren't starved at busy stops.

| Filter | Matching | Example |
|--------|----------|---------|
| **Line filter** | Exact line name, case-insensitive | `U79, RE5` |
| **Destination filter** | Substring of the destination, case-insensitive | `Duisburg, Airport` |
| **Platform filter** | Exact platform/track | `3, 4` |

#### Platform filter

Filtering by platform is often more stable than filtering by destination: the same direction
can appear under many different destination strings (shortened names, special services,
temporary changes), while the track number usually stays put.

The value is matched against the provider's technical platform identifier — the same value
you see in the `platform` attribute of the departures list. Common labels are stripped before
comparing, so `3`, `Gleis 3` and `gleis 3` all match the same track.

!!! note
    At larger stations the same platform number can exist more than once — track 3 for rail
    and stop position 3 for buses, for example. The filter cannot tell those apart on its own;
    combine it with the **Transportation types** selector when the number is ambiguous.

!!! tip
    Not every provider returns platform data. Check the `platform` attribute of your
    departures sensor first — if it is empty, this filter will match nothing.
