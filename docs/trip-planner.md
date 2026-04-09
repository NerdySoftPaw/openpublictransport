# Trip Planner

Plan routes from A to B with real-time connection monitoring, transfer risk assessment, and delay tracking.

## Overview

The Trip Planner feature lets you:

- **Plan trips** between any two stops via the `openpublictransport.plan_trip` service call
- **Monitor connections** with a persistent trip sensor that updates automatically
- **Assess transfer risk** -- each connection is rated as `low`, `medium`, `high`, or `missed`
- **Track delays** in real time across all legs of your journey

## Supported Providers

The Trip Planner works with all EFA-based providers:

| Provider | Region |
|----------|--------|
| VRR | Rhein-Ruhr (NRW) |
| KVV | Karlsruhe |
| HVV | Hamburg |
| MVV | Munich |
| VVS | Stuttgart |
| VAG | Freiburg |

## Setting Up a Trip Sensor

A trip sensor gives you a persistent entity that always shows the next best connection for a configured route.

### Via Config Flow

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Public Transport Departures"
4. Select your provider
5. Choose **"Trip Planner"** as the sensor type
6. Enter origin stop and city
7. Enter destination stop and city
8. Configure update interval

The sensor will appear as `sensor.openpublictransport_trip_<origin>_to_<destination>`.

### Example Sensor State and Attributes

**State:** `08:15 - U79 to Duisburg Meiderich`

**Attributes:**

```json
{
  "origin": "Holthausen, Dusseldorf",
  "destination": "Hauptbahnhof, Dusseldorf",
  "departure_time": "2026-04-09T08:15:00+02:00",
  "arrival_time": "2026-04-09T08:42:00+02:00",
  "duration_minutes": 27,
  "transfers": 1,
  "connection_feasible": true,
  "transfer_risk": "low",
  "legs": [
    {
      "line": "U79",
      "direction": "Duisburg Meiderich",
      "departure_stop": "Holthausen",
      "departure_time": "08:15",
      "arrival_stop": "Dusseldorf Hbf",
      "arrival_time": "08:35",
      "delay": 2,
      "platform": "1"
    },
    {
      "line": "RE5",
      "direction": "Koblenz Hbf",
      "departure_stop": "Dusseldorf Hbf",
      "departure_time": "08:40",
      "arrival_stop": "Dusseldorf Hbf",
      "arrival_time": "08:42",
      "delay": 0,
      "platform": "3"
    }
  ],
  "next_connections": [
    {
      "departure_time": "08:30",
      "arrival_time": "08:57",
      "transfers": 1,
      "transfer_risk": "low"
    }
  ]
}
```

## Using the plan_trip Service

You can also plan trips on demand via a service call.

### Service Call

```yaml
service: openpublictransport.plan_trip
data:
  provider: vrr
  origin: Holthausen
  origin_city: Dusseldorf
  destination: Hauptbahnhof
  destination_city: Dusseldorf
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `provider` | Yes | Provider ID (`vrr`, `kvv`, `mvv`, `vvs`, `vagfr`, `hvv`) |
| `origin` | Yes | Origin stop name |
| `origin_city` | No | City of origin stop (improves accuracy) |
| `destination` | Yes | Destination stop name |
| `destination_city` | No | City of destination stop (improves accuracy) |

The service fires an `openpublictransport_trip_result` event with the trip data.

## Connection Monitoring

Every trip result includes transfer risk assessment:

| Risk Level | Meaning |
|------------|---------|
| `low` | Comfortable transfer time (>5 min buffer) |
| `medium` | Tight but feasible (2-5 min buffer) |
| `high` | At risk due to delays (<2 min buffer) |
| `missed` | Connection is no longer reachable |

The `connection_feasible` attribute is `true` when all transfers can still be made, and `false` when any transfer is missed.

## Example Automations

### Notify When Connection Is at Risk

```yaml
automation:
  - alias: "Warn about risky connection"
    trigger:
      - platform: state
        entity_id: sensor.openpublictransport_trip_holthausen_to_hauptbahnhof
        attribute: transfer_risk
        to: "high"
    action:
      - service: notify.mobile_app
        data:
          title: "Connection at risk!"
          message: >
            Your transfer at {{ state_attr('sensor.openpublictransport_trip_holthausen_to_hauptbahnhof', 'legs')[0]['arrival_stop'] }}
            is at risk. Consider taking an earlier connection.
```

### Morning Commute Check

```yaml
automation:
  - alias: "Morning commute notification"
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: time
        weekday: [mon, tue, wed, thu, fri]
    action:
      - service: openpublictransport.plan_trip
        data:
          provider: vrr
          origin: Holthausen
          origin_city: Dusseldorf
          destination: Hauptbahnhof
          destination_city: Dusseldorf
      - delay:
          seconds: 3
      - service: notify.mobile_app
        data:
          title: "Commute Update"
          message: >
            Next connection: {{ states('sensor.openpublictransport_trip_holthausen_to_hauptbahnhof') }}
            ({{ state_attr('sensor.openpublictransport_trip_holthausen_to_hauptbahnhof', 'duration_minutes') }} min,
            {{ state_attr('sensor.openpublictransport_trip_holthausen_to_hauptbahnhof', 'transfers') }} transfer(s),
            risk: {{ state_attr('sensor.openpublictransport_trip_holthausen_to_hauptbahnhof', 'transfer_risk') }})
```

### Alert on Missed Connection

```yaml
automation:
  - alias: "Missed connection alert"
    trigger:
      - platform: state
        entity_id: sensor.openpublictransport_trip_holthausen_to_hauptbahnhof
        attribute: connection_feasible
        to: "False"
    action:
      - service: notify.mobile_app
        data:
          title: "Connection missed"
          message: "Your planned connection is no longer feasible. Check the app for alternatives."
```
