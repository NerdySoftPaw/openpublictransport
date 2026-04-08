# Services

The integration provides a service to manually refresh departure data.

## openpublictransport.refresh_departures

Manually refresh departure data from the API outside of the normal update interval.

### Description

This service triggers an immediate API call to fetch the latest departure information. Use this when you need up-to-date data without waiting for the next scheduled update.

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `entity_id` | No | Specific entity to refresh. If omitted, all entities are refreshed. |

### Examples

#### Refresh All Sensors

```yaml
service: openpublictransport.refresh_departures
```

#### Refresh Specific Sensor

```yaml
service: openpublictransport.refresh_departures
data:
  entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
```

#### Refresh Multiple Sensors

```yaml
service: openpublictransport.refresh_departures
data:
  entity_id:
    - sensor.openpublictransport_dusseldorf_hauptbahnhof
    - sensor.openpublictransport_essen_hauptbahnhof
```

### Use Cases

#### Button Card for Manual Refresh

Create a button in your dashboard to manually refresh data:

```yaml
type: button
name: Refresh Departures
icon: mdi:refresh
tap_action:
  action: call-service
  service: openpublictransport.refresh_departures
  service_data:
    entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
```

#### Automation: Refresh When Arriving Home

```yaml
automation:
  - alias: "Refresh departures when arriving home"
    trigger:
      - platform: state
        entity_id: person.john
        to: home
    action:
      - service: openpublictransport.refresh_departures
        data:
          entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
```

#### Automation: Refresh Before Morning Commute

```yaml
automation:
  - alias: "Refresh departures before commute"
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: openpublictransport.refresh_departures
        data:
          entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
```

#### Script: Refresh and Notify

```yaml
script:
  refresh_and_notify_departures:
    alias: "Refresh and Notify Departures"
    sequence:
      - service: openpublictransport.refresh_departures
        data:
          entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
      - delay:
          seconds: 2
      - service: notify.mobile_app
        data:
          title: "Next Departure"
          message: >
            {{ states('sensor.openpublictransport_dusseldorf_hauptbahnhof') }} -
            {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'next_departure_minutes') }} min
```

### Rate Limiting Considerations

!!! warning
    While the refresh service bypasses the normal update interval, it still counts against the daily API rate limit.

- Each refresh counts as one API call
- The integration tracks daily API calls
- If the rate limit is reached, refreshes will fail
- A repair issue will be created if rate limiting is triggered

### Best Practices

1. **Don't call too frequently** - Give time for API response before triggering again
2. **Use in specific scenarios** - Arriving home, before leaving, etc.
3. **Combine with normal updates** - Don't rely solely on manual refreshes
4. **Monitor API usage** - Check the diagnostics for call counts
