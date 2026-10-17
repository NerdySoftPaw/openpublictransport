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
| `provider` | Yes | Provider ID of a trip-capable provider (e.g. `vrr`, `kvv`, `mvv`, `vgn`, `openpublictransport`) — see [Trip Planner](trip-planner.md#supported-providers) |
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

---

## openpublictransport.get_journeys

Return every connection a trip sensor is currently holding, each with its legs.

### Description

A trip sensor publishes the legs of the first connection and no more than a summary of the alternatives — departure, arrival, duration, transfers, transfer risk. That is deliberate: every attribute is written to the recorder on each state change, and carrying the legs of four connections would roughly triple what a trip sensor stores. The detail is not missing, though, only unpublished: the coordinator keeps every connection whole between polls, and this action hands it over.

It costs no request to the provider. It also cannot disagree with what the sensor is showing — the connections have already had the departed ones dropped and the entry's line and transport-type filters applied, which a fresh `plan_trip` would not have.

This action returns a response, so it must be called with `response_variable` (in the UI: *Actions → openpublictransport.get_journeys*, then enable the response). Calling it without one is rejected rather than silently doing nothing.

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `entity_id` | Yes | The trip sensor to read. A departure board is rejected — it has no journeys. |

### Example Call

```yaml
action: openpublictransport.get_journeys
data:
  entity_id: sensor.trip_station_to_station
response_variable: trip
```

### Response

The same journey structure `plan_trip` returns, for every connection the sensor holds — the one in the sensor's own attributes first, then the alternatives:

```json
{
  "journeys": [
    {
      "id": "a3f19c4e7b02",
      "departure": "09:42",
      "arrival": "10:21",
      "departure_timestamp": "2026-09-20T09:42:00+02:00",
      "arrival_timestamp": "2026-09-20T10:21:00+02:00",
      "duration_minutes": 39,
      "transfers": 1,
      "connection_feasible": true,
      "transfer_risk": "low",
      "min_transfer_time": 6,
      "legs": [
        {
          "origin": "Köln Hbf",
          "destination": "Düsseldorf Hbf",
          "line": "RE1",
          "direction": "Hamm (Westf) Hbf",
          "product": "Regional-Express",
          "transport_type": "train",
          "departure_planned": "09:42",
          "departure_estimated": "09:46",
          "arrival_planned": "09:50",
          "arrival_estimated": "09:54",
          "delay": 4,
          "duration_minutes": 8,
          "platform": "2",
          "transfer": "Fussweg",
          "transfer_minutes": 6
        }
      ]
    }
  ]
}
```

An empty list means the sensor has no connections to offer — either the provider found none, or its last update failed, in which case the entity is unavailable anyway.

### Matching a Journey

`id` identifies a connection. It is derived from the journey's own route — each leg's line, where it is boarded and when it is timetabled to leave — so it is stable while a delay estimate moves, and the same alternatives carry it in the sensor's `next_journeys`. A caller that showed a summary earlier and wants its detail now looks the journey up by `id`.

Nothing else identifies one. A position in the list does not, because the first connection rolls off as it departs. Neither does `departure_timestamp`: a board regularly holds two connections leaving on the same minute — a live VVS board had three such pairs among seven connections — and even departure, arrival, transfers and duration together can describe two different routes on parallel lines. When the `id` is not found, say the connection is gone rather than describing whichever journey took its place.

---

## openpublictransport.check_delays

Check for delayed departures and fire an `openpublictransport_delay_alert` event.

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `entity_id` | Yes | Sensor entity to check |
| `delay_threshold` | No | Minimum delay in minutes to count as delayed (default: 5) |
| `line` | No | Filter to a specific line (e.g. `U79`) |

### Example Call

```yaml
service: openpublictransport.check_delays
data:
  entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
  delay_threshold: 5
  line: "U79"
```

### Response

Returns a list of delayed departures. Additionally fires an `openpublictransport_delay_alert` event with:

| Field | Description |
|-------|-------------|
| `entity_id` | The checked entity |
| `delayed_count` | Number of delayed departures |
| `max_delay` | Highest delay in minutes |
| `lines` | List of affected lines |
| `departures` | Full list of delayed departure objects |

### Example Automation

```yaml
automation:
  - alias: "Notify on checked delays"
    trigger:
      - platform: event
        event_type: openpublictransport_delay_alert
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.delayed_count > 0 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Delay Alert"
          message: >
            {{ trigger.event.data.delayed_count }} delayed departure(s).
            Max delay: {{ trigger.event.data.max_delay }} min.
            Lines: {{ trigger.event.data.lines | join(', ') }}
```

---

## openpublictransport.announce_departure

Get a spoken-language departure announcement for use with any TTS service.

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `entity_id` | Yes | Sensor entity to announce from |
| `index` | No | Departure index (default: 0 = next departure) |

### Example Call

```yaml
service: openpublictransport.announce_departure
data:
  entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
  index: 0
```

### Response

```json
{
  "text": "U79 Richtung Wittlaer fährt in 3 Minuten von Gleis 2. Verspätung: 3 Minuten."
}
```

### TTS Automation Example

```yaml
automation:
  - alias: "Morning TTS departure announcement"
    trigger:
      - platform: time
        at: "07:30:00"
    condition:
      - condition: time
        weekday: [mon, tue, wed, thu, fri]
    action:
      - service: openpublictransport.announce_departure
        data:
          entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
          index: 0
        response_variable: result
      - service: tts.speak
        target:
          entity_id: tts.google_translate
        data:
          message: "{{ result.text }}"
```
