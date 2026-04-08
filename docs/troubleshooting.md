# Troubleshooting

This guide helps you diagnose and resolve common issues with the Public Transport Integration.

## Common Issues

### "No departures" State

**Symptoms**: Sensor shows "No departures" even when the station is active.

**Possible Causes**:

1. **Invalid Station ID**: The station ID may be incorrect or have changed
2. **API Issues**: The provider's API may be temporarily unavailable
3. **Filter Too Restrictive**: Transportation type filters may exclude all departures
4. **Off-Peak Hours**: Some stations have no service during certain hours

**Solutions**:

1. Verify the station exists and is spelled correctly
2. Check the provider's API status
3. Remove transportation type filters temporarily
4. Enable debug logging to see API responses

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

### Connection Errors

**Symptoms**: "API connection error" or timeout messages.

**Possible Causes**:

- Network connectivity issues
- Provider API downtime
- Firewall blocking connections

**Solutions**:

1. Check your internet connection
2. Verify the provider's API is accessible
3. Check for firewall rules blocking outgoing connections

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
