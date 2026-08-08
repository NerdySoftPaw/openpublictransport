# Trip Planner

Plan routes from A to B with real-time connection monitoring, transfer risk assessment, and delay tracking.

## Overview

The Trip Planner feature lets you:

- **Plan trips** between any two stops via the `openpublictransport.plan_trip` service call
- **Monitor connections** with a persistent trip sensor that updates automatically
- **Assess transfer risk** -- each connection is rated as `low`, `medium`, `high`, or `missed`
- **Track delays** in real time across all legs of your journey

## Supported Providers

Trip planning needs a routing endpoint, which only part of the providers offer. Two
families are supported: EFA providers with an `XML_TRIP_REQUEST2` endpoint, and OTP2
providers.

### EFA providers

| Provider | Provider ID | Region |
|----------|-------------|--------|
| VRR | `vrr` | Rhein-Ruhr (NRW) |
| KVV | `kvv` | Karlsruhe |
| HVV | `hvv` | Hamburg |
| MVV | `mvv` | Munich |
| VVS | `vvs` | Stuttgart |
| VGN | `vgn` | Nuremberg |
| VAG | `vagfr` | Freiburg |
| VRN | `vrn` | Rhein-Neckar |
| VVO | `vvo` | Dresden |
| DING | `ding` | Ulm |
| AVV | `avv_augsburg` | Augsburg |
| RVV | `rvv` | Regensburg |
| BSVG | `bsvg` | Braunschweig |
| NWL | `nwl` | Westfalen-Lippe |

### OTP providers

| Provider | Provider ID | Region |
|----------|-------------|--------|
| openpublictransport | `openpublictransport` | Germany (nationwide, community OTP2 server) |
| OTP2 Custom | `otp_custom` | Any self-hosted OTP2 instance |
| VBN | `vbn_otp` | Bremen / Niedersachsen |

OTP trip planning routes stop to stop, so both stops must be picked in the config flow
(or passed as stop IDs) — a plain name search is not enough.

!!! note "Departure monitor only"

    All other providers — including ÖBB, NS, mobilitéit.lu, SBB, BVG, DB, RMV, NVBW,
    BEG, Transitous, Entur and the GTFS-RT/HAFAS providers — have no routing endpoint
    in this integration. They only power the departure monitor. Selecting the Trip
    Planner entry type for them is rejected in the config flow.

## Setting Up a Trip Sensor

A trip sensor gives you a persistent entity that always shows the next best connection for a configured route.

### Via Config Flow

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Public Transport Departures"
4. Select your provider and choose **"Verbindungssuche / Trip Planner"** as the entry type:

    ![Trip mode selection](assets/screenshots/config-flow/07-trip-provider-select.png)

5. Enter origin stop name:

    ![Origin search](assets/screenshots/config-flow/09-trip-origin-search.png)

6. Enter destination stop name
7. Configure update interval

The sensor will appear as `sensor.openpublictransport_trip_<origin>_to_<destination>`.

### Example Sensor State and Attributes

**State:** `08:15 → 08:42 (27 min, 1 transfers)`

**Attributes:**

```json
{
  "origin": "Holthausen, Dusseldorf",
  "destination": "Hauptbahnhof, Dusseldorf",
  "departure": "08:15",
  "arrival": "08:42",
  "departure_timestamp": "2026-04-09T08:15:00+02:00",
  "arrival_timestamp": "2026-04-09T08:42:00+02:00",
  "in_minutes": 6,
  "duration_minutes": 27,
  "transfers": 1,
  "connection_feasible": true,
  "transfer_risk": "low",
  "min_transfer_time": 5,
  "legs": [
    {
      "origin": "Holthausen",
      "destination": "Dusseldorf Hbf",
      "line": "U79",
      "product": "U-Bahn",
      "departure_planned": "08:15",
      "departure_estimated": "08:17",
      "arrival_planned": "08:35",
      "arrival_estimated": "08:35",
      "delay": 2,
      "duration_minutes": 20,
      "platform": "1"
    },
    {
      "origin": "Dusseldorf Hbf",
      "destination": "Hauptbahnhof",
      "line": "RE5",
      "product": "Regional",
      "departure_planned": "08:40",
      "departure_estimated": "08:40",
      "arrival_planned": "08:42",
      "arrival_estimated": "08:42",
      "delay": 0,
      "duration_minutes": 2,
      "platform": "3"
    }
  ],
  "alternative_journeys": 3,
  "next_journeys": [
    {
      "departure": "08:30",
      "arrival": "08:57",
      "departure_timestamp": "2026-04-09T08:30:00+02:00",
      "arrival_timestamp": "2026-04-09T08:57:00+02:00",
      "in_minutes": 21,
      "duration_minutes": 27,
      "transfers": 1,
      "transfer_risk": "low"
    }
  ]
}
```

`departure` / `arrival` are `HH:MM` for display. Use `departure_timestamp` and `in_minutes` when
you need to compare against the current time — a bare `HH:MM` cannot tell 23:50 tonight from
23:50 tomorrow.

Both `departure` and `in_minutes` refer to the **start of the journey**. On some providers that
is a footpath to the platform, so the countdown is to when you have to set off, not to when the
vehicle leaves.

Connections that have already departed are not reported — the sensor always shows the next one
you can still reach.

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
| `low` | Comfortable transfer time (more than 5 min), or no transfer at all |
| `medium` | Tight but feasible (4-5 min) |
| `high` | At risk due to delays (1-3 min) |
| `missed` | Connection is no longer reachable (0 min or less) |

The rating uses the gap between two **vehicles**, reported as `min_transfer_time` (`null` for a
direct connection). A walk to the platform is not a transfer — it ends exactly when the
connecting vehicle leaves, and rating it as one would mark every walk-in journey as `missed`.

The `connection_feasible` attribute is `true` when all transfers can still be made, and `false` when any transfer is missed.

## Walking Time

The **walking time** option (**Configure** on the trip entry) is the time you need to reach the
origin stop. It shifts the search and hides connections you could not reach in time, so a trip
sensor with 10 minutes walking time never shows a connection leaving in 5 minutes.

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
