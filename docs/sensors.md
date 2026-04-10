# Sensors & Attributes

The integration creates up to **7 entity types** for each configured stop:

| Entity Type | Description |
|-------------|-------------|
| **Sensor** | Next departure time with full departure list |
| **Binary Sensor** | Delay detection (configurable threshold) |
| **Calendar** | Each departure as a calendar event |
| **Event** | Fires on disruption notices |
| **Camera** | Rendered departure board image (yellow-on-black) |
| **Trip Sensor** | Route A→B with transfers and delays |
| **Statistics** | Per-line punctuality tracking |

## Sensor Entity

### State

The sensor's state is the departure time of the next departure (e.g., "14:35") or "No departures" if none are available.

### Icon

The icon dynamically changes based on the transportation type of the next departure:

| Transport Type | Icon |
|----------------|------|
| bus | mdi:bus-clock |
| tram | mdi:tram |
| subway | mdi:subway-variant |
| train | mdi:train |
| ferry | mdi:ferry |
| taxi | mdi:taxi |
| on_demand | mdi:bus-alert |

### Entity Picture

If "Use provider logo" is enabled in options, the entity displays the provider's logo instead of the dynamic icon.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `departures` | List | Full list of upcoming departures |
| `next_3_departures` | List | Simplified list of next 3 departures |
| `station_name` | String | Name of the station |
| `station_id` | String | Station ID |
| `last_updated` | DateTime | Last successful update time |
| `next_departure_minutes` | Integer | Minutes until next departure |
| `total_departures` | Integer | Number of departures in list |
| `delayed_count` | Integer | Count of delayed departures |
| `on_time_count` | Integer | Count of on-time departures |
| `average_delay` | Float | Average delay in minutes |
| `earliest_departure` | String | Time of earliest departure (HH:MM) |
| `latest_departure` | String | Time of latest departure (HH:MM) |

### Departure Object Structure

Each departure in the `departures` list contains:

| Field | Type | Description |
|-------|------|-------------|
| `line` | String | Line number/name (e.g., "U1", "RE5", "Bus 42") |
| `destination` | String | Final destination |
| `departure_time` | String | Actual/estimated departure time (HH:MM) |
| `planned_time` | String | Scheduled departure time (HH:MM) |
| `delay` | Integer | Delay in minutes (0 if on time) |
| `platform` | String | Platform/track number |
| `transportation_type` | String | Type: bus, train, tram, subway, ferry, taxi |
| `is_realtime` | Boolean | Whether real-time data is available |
| `minutes_until_departure` | Integer | Minutes until departure |
| `description` | String | Route description (optional) |
| `agency` | String | Operating agency (NTA only) |

### Example Attribute Data

```json
{
  "departures": [
    {
      "line": "U79",
      "destination": "Düsseldorf Hbf",
      "departure_time": "14:35",
      "planned_time": "14:33",
      "delay": 2,
      "platform": "1",
      "transportation_type": "subway",
      "is_realtime": true,
      "minutes_until_departure": 5
    },
    {
      "line": "RE5",
      "destination": "Koblenz Hbf",
      "departure_time": "14:42",
      "planned_time": "14:42",
      "delay": 0,
      "platform": "3",
      "transportation_type": "train",
      "is_realtime": true,
      "minutes_until_departure": 12
    }
  ],
  "next_3_departures": [...],
  "station_name": "Düsseldorf - Hauptbahnhof",
  "station_id": "20018235",
  "last_updated": "2025-01-22T14:30:00+01:00",
  "next_departure_minutes": 5,
  "total_departures": 10,
  "delayed_count": 3,
  "on_time_count": 7,
  "average_delay": 2.3,
  "earliest_departure": "14:35",
  "latest_departure": "15:15"
}
```

## Binary Sensor Entity

The binary sensor indicates whether there are significant delays at the stop.

### State

- **On** (Problem): At least one departure has a delay > 5 minutes
- **Off** (OK): All departures are on time or have minor delays

### Device Class

`problem` - Displays as a problem indicator in the Home Assistant UI.

### Icon

| State | Icon |
|-------|------|
| On (delayed) | mdi:alert-circle |
| Off (on time) | mdi:check-circle |

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `delayed_departures` | Integer | Count of delayed departures |
| `on_time_departures` | Integer | Count of on-time departures |
| `average_delay` | Float | Average delay in minutes |
| `max_delay` | Integer | Maximum delay in minutes |
| `total_departures` | Integer | Total number of departures |
| `delays_list` | List | First 10 delay values |
| `delay_threshold` | Integer | Threshold for triggering (5 minutes) |

### Example

```json
{
  "delayed_departures": 2,
  "on_time_departures": 8,
  "average_delay": 3.5,
  "max_delay": 12,
  "total_departures": 10,
  "delays_list": [12, 3],
  "delay_threshold": 5
}
```

## Statistics Sensor

A separate statistics sensor is created for each configured stop: `sensor.*_statistics`.

### State

Overall punctuality percentage (%). Delays of 2 minutes or less are considered on-time.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `lines` | Dict | Per-line statistics (see below) |

Each entry in `lines` contains:

| Field | Type | Description |
|-------|------|-------------|
| `total` | Integer | Total observed departures for the line |
| `on_time` | Integer | Departures with delay <= 2 min |
| `punctuality` | Float | Punctuality percentage for the line |
| `average_delay` | Float | Average delay in minutes for the line |

### Example

```json
{
  "state": "87.5",
  "attributes": {
    "lines": {
      "U79": {
        "total": 40,
        "on_time": 36,
        "punctuality": 90.0,
        "average_delay": 1.8
      },
      "RE5": {
        "total": 20,
        "on_time": 15,
        "punctuality": 75.0,
        "average_delay": 4.2
      }
    }
  }
}
```

### Template Sensor Example

```yaml
template:
  - sensor:
      - name: "U79 Punctuality"
        state: >
          {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof_statistics', 'lines').U79.punctuality }}
        unit_of_measurement: "%"
        icon: mdi:chart-line
```

## Device Grouping

Both entities are grouped under a single device:

- **Device Name**: `{place} - {stop_name}`
- **Manufacturer**: `{PROVIDER} Public Transport`
- **Model**: `Departure Monitor`
- **Suggested Area**: The city/place name

This grouping makes it easy to manage multiple stops and see all related entities together.

## Template Sensor Examples

### Minutes Until Departure

```yaml
template:
  - sensor:
      - name: "Next Train Minutes"
        state: >
          {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'next_departure_minutes') }}
        unit_of_measurement: "min"
        icon: mdi:clock-outline
```

### Next Line Number

```yaml
template:
  - sensor:
      - name: "Next Train Line"
        state: >
          {% set departures = state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'departures') %}
          {% if departures and departures|length > 0 %}
            {{ departures[0].line }}
          {% else %}
            -
          {% endif %}
        icon: mdi:train
```

### Delayed Departure Count

```yaml
template:
  - sensor:
      - name: "Delayed Departures"
        state: >
          {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'delayed_count') }}
        unit_of_measurement: "departures"
        icon: mdi:clock-alert
```
