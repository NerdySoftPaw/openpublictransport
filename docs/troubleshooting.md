# Troubleshooting

This guide helps you diagnose and resolve common issues with the Public Transport Integration.

## Common Issues

### Setup shows an error while searching for a stop

Since v2026.9.0 each kind of failure has its own message, so the error tells you what to do
next. Before that release every one of them read "no results found", which sent people hunting
for a better search term during a provider outage.

| Message | What happened | What to do |
|---|---|---|
| Fehler beim Anbieter (HTTP `nnn`) | The provider answered with an error. `503` means its API is down or restarting; `404` means the endpoint moved or no longer exists. | For `5xx`, wait and try again. If a `404` persists, open an issue — the provider has probably changed its endpoint. |
| Authentifizierung fehlgeschlagen | The API key was rejected (HTTP 401/403). | Check the key for typos and that it is still valid. Some providers expire unused keys. |
| Der Anbieter ist nicht erreichbar | The request timed out or the host could not be reached at all. | Check your Home Assistant host's internet access and DNS. For a self-hosted OTP2 instance, check the URL, the port and any firewall. |
| Der Anbieter hat eine unbrauchbare Antwort geliefert | The provider answered with `200` but the body could not be parsed. | Usually a maintenance page served in place of the API. Wait and retry; if it persists, open an issue with a debug log. |
| Keine Ergebnisse gefunden | The provider answered normally and had no match. | This one really is about the search term — try the plain stop name without the city, or `Stop, City`. |

A failed search is never cached, so retrying after an outage really does query the provider
again.

### "No departures" State

**Symptoms**: Sensor shows "No departures" even when the station is active.

**Possible Causes**:

1. **Filter Too Restrictive**: Transportation type, line, destination or platform filters may
   exclude every departure
2. **Off-Peak Hours**: Some stations have no service during certain hours
3. **Invalid Station ID**: The station ID may be incorrect or have changed

**Solutions**:

1. Remove the filters temporarily to see the raw board
2. Check whether the station is served at all at this time of day
3. Enable debug logging to see the API response

!!! note
    An API failure no longer shows up as "No departures". Since v2026.9.0 the sensor goes
    **unavailable** instead, the log names the HTTP status, and a repair issue appears — so an
    empty board means the station really has no departures right now.

### API Rate Limit Reached

**Symptoms**: Integration stops updating, repair issue created.

**Possible Causes**:

- Too many sensors configured
- Scan interval too low
- Too many manual refreshes

**Solutions**:

1. Increase the scan interval (e.g., from 60s to 120s)
2. Reduce the number of configured sensors
3. Wait until the next day (limits reset daily)

### "Unknown" Transportation Types

**Symptoms**: Debug logs show "Unknown transport class X".

**Cause**: The provider uses a transport class not yet mapped in the integration.

**Solution**: Report the issue on GitHub with:

- The provider you're using
- The unknown class number
- The type of transport it should represent

### Scheduled Maintenance (Sunday ~2:00 AM)

**Symptoms**: All sensors show connection errors or stop updating simultaneously, then recover automatically after ~80 minutes.

**Cause**: The `openpublictransport` community server rebuilds its routing graph every Sunday around 2:00 AM (Europe/Berlin). During this window the API is completely offline.

**Action**: None required — the API recovers automatically. If automations are scheduled for Sunday early morning, move them to after 4:00 AM.

!!! note
    This only affects the **openpublictransport (Community Server)** provider. All other providers are unaffected.

### Connection Errors

**Symptoms**: The sensor is **unavailable** and a repair issue appears. The log carries the
reason, with the HTTP status when the provider answered at all:

```
kvv: unavailable (HTTP 503) — will retry
```

**Possible Causes**:

- Provider API downtime (see scheduled maintenance above)
- Network connectivity issues
- Firewall blocking outgoing connections

**Solutions**:

1. Read the status in the log — `5xx` is the provider's side, `401`/`403` is your API key,
   a timeout is usually the network in between
2. Check your internet connection and whether the provider's API is reachable from the
   Home Assistant host
3. Check for firewall rules blocking outgoing connections

The integration retries on its own and logs once when the provider is unavailable and once when
it is back, so a short outage needs no action. The repair issue disappears on recovery.

!!! note
    A rejected API key (HTTP 401/403) does not just mark the entity unavailable — it starts a
    reauthentication flow, so Home Assistant asks you for a new key directly.

## Debug Logging

Enable debug logging to see detailed information about API calls and responses.

Add to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.openpublictransport: debug
```

After restarting Home Assistant, check the logs for detailed information.

### What to Look For

- **API URLs**: Verify the correct endpoint is being called
- **Response Status**: Look for non-200 status codes
- **Response Content**: Check if the API returns expected data
- **Transport Class Mapping**: See how departures are being classified

## Diagnostics

The integration supports Home Assistant's diagnostics feature for easier troubleshooting.

### How to Download Diagnostics

1. Go to **Settings** > **Devices & Services**
2. Find your Public Transport Departures integration
3. Click on the integration
4. Click the **3 dots** menu
5. Select **Download Diagnostics**

### Diagnostics Contents

The diagnostics file contains:

- Configuration details (anonymized)
- Coordinator status
- API call statistics
- Sample API response structure
- Last update information

This information is helpful when reporting issues on GitHub.

## Provider-Specific Issues

### VRR / KVV / HVV

**Stop not found**: Try different spellings or include the city name.

```
"Hauptbahnhof" → "Düsseldorf Hauptbahnhof"
"Hbf" → "Hauptbahnhof"
```

!!! tip "Use 'Stop, City' format for better results"
    If your search returns too many or inaccurate results, use the comma-separated format: `Holthausen, Düsseldorf`. The integration splits this into a stop name and a city filter, which narrows results significantly.

**Platform information missing**: Some stops don't provide platform data in the API response.

### Trafiklab (Sweden)

**401 Authentication Error**:

1. Verify your API key is correct
2. Check that the key is active in your Trafiklab project
3. Ensure you're using the Realtime API key

**Empty Results**: Use Swedish names and spellings for locations.

### NTA (Ireland)

**No Departures Found**:

1. Verify the stop ID format is correct
2. GTFS stop IDs may differ from displayed stop numbers
3. Check that the stop has active services

**Secondary Key Fallback**: If primary key fails, the integration automatically tries the secondary key.

## API Testing

### Finding Station IDs

#### VRR

Use the STOPFINDER API:

```
https://openservice-test.vrr.de/static03/XML_STOPFINDER_REQUEST?outputFormat=RapidJSON&locationServerActive=1&type_sf=stop&name_sf=Düsseldorf%20Hauptbahnhof
```

#### Testing Departures

VRR/KVV/HVV using Station ID:

```
https://openservice-test.vrr.de/static03/XML_DM_REQUEST?outputFormat=RapidJSON&stateless=1&type_dm=any&name_dm=20018235&mode=direct&useRealtime=1&limit=10
```

VRR/KVV/HVV using Place and Name:

```
https://openservice-test.vrr.de/static03/XML_DM_REQUEST?outputFormat=RapidJSON&place_dm=Düsseldorf&type_dm=stop&name_dm=Hauptbahnhof&mode=direct&useRealtime=1&limit=10
```

## FAQ

### Can I monitor multiple stops?

Yes! Add the integration multiple times, once for each stop.

### Why are some departures missing?

They may be filtered by the transportation type setting. Check your configuration options.

### How often does data update?

Based on your configured scan interval (default: 60 seconds).

### What's the difference between planned and departure time?

- **Planned time**: The scheduled departure time
- **Departure time**: The actual/estimated departure time (includes delays)

### Why is my delay sensor always off?

The binary sensor only activates when delays exceed 5 minutes.

## Reporting Issues

When reporting issues on GitHub, please include:

1. **Home Assistant version**
2. **Integration version**
3. **Provider** you're using
4. **Debug logs** (with sensitive data removed)
5. **Diagnostics file** (if possible)
6. **Steps to reproduce** the issue

### Sensitive Data

Before sharing logs or diagnostics:

- Remove or replace API keys
- Remove personal location information if desired
- Check for any other sensitive data

## Getting Help

1. Check this troubleshooting guide first
2. Search existing [GitHub Issues](https://github.com/NerdySoftPaw/openpublictransport/issues)
3. Create a new issue with detailed information
