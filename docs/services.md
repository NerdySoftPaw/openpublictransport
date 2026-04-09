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

---

## openpublictransport.plan_trip

Plan a route from origin to destination, returning connections with transfers and real-time delay information.

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `provider` | Yes | Provider ID (e.g. `vrr`, `kvv`, `mvv`, `vvs`, `vagfr`, `hvv`) |
| `origin` | Yes | Origin stop name (e.g. `Holthausen`) |
| `origin_city` | No | City of origin stop for more precise results |
| `destination` | Yes | Destination stop name (e.g. `Hauptbahnhof`) |
| `destination_city` | No | City of destination stop for more precise results |

### Examples

#### Basic Trip Query

```yaml
service: openpublictransport.plan_trip
data:
  provider: vrr
  origin: Holthausen
  origin_city: Düsseldorf
  destination: Hauptbahnhof
  destination_city: Düsseldorf
```

#### Cross-City Trip

```yaml
service: openpublictransport.plan_trip
data:
  provider: vrr
  origin: Hauptbahnhof
  origin_city: Düsseldorf
  destination: Hauptbahnhof
  destination_city: Essen
```

### Example Response

The service returns trip data via a `openpublictransport_trip_result` event:

```json
{
  "origin": "Holthausen, Düsseldorf",
  "destination": "Hauptbahnhof, Düsseldorf",
  "departure_time": "2026-04-09T08:15:00+02:00",
  "arrival_time": "2026-04-09T08:42:00+02:00",
  "duration_minutes": 27,
  "transfers": 1,
  "legs": [
    {
      "line": "U79",
      "direction": "Duisburg Meiderich",
      "departure_stop": "Holthausen",
      "departure_time": "08:15",
      "arrival_stop": "Düsseldorf Hbf",
      "arrival_time": "08:35",
      "delay": 2,
      "platform": "1"
    },
    {
      "line": "RE5",
      "direction": "Koblenz Hbf",
      "departure_stop": "Düsseldorf Hbf",
      "departure_time": "08:40",
      "arrival_stop": "Düsseldorf Hbf",
      "arrival_time": "08:42",
      "delay": 0,
      "platform": "3"
    }
  ],
  "connection_feasible": true,
  "transfer_risk": "low"
}
```

### Use in Automation

```yaml
automation:
  - alias: "Plan morning commute"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: openpublictransport.plan_trip
        data:
          provider: vrr
          origin: Holthausen
          origin_city: Düsseldorf
          destination: Hauptbahnhof
          destination_city: Düsseldorf
```

For full details see the [Trip Planner guide](trip-planner.md).
