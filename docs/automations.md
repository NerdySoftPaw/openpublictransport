# Automations

This page provides automation examples for the Public Transport Integration.

## Refresh Departures

### Refresh When Arriving Home

Automatically refresh departure data when you arrive home.

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

### Refresh Before Morning Commute

Refresh data before your morning commute on weekdays.

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

## Delay Notifications

### Notify on Significant Delays

Send a notification when delays exceed 5 minutes.

```yaml
automation:
  - alias: "Notify on train delays"
    trigger:
      - platform: state
        entity_id: binary_sensor.openpublictransport_dusseldorf_hauptbahnhof_delays
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Train Delays"
          message: >
            Delays detected at {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'station_name') }}.
            Maximum delay: {{ state_attr('binary_sensor.openpublictransport_dusseldorf_hauptbahnhof_delays', 'max_delay') }} minutes.
```

### Morning Delay Alert

Alert you about delays during your commute time.

```yaml
automation:
  - alias: "Morning commute delay alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.openpublictransport_dusseldorf_hauptbahnhof_delays
        to: "on"
    condition:
      - condition: time
        after: "06:30:00"
        before: "09:00:00"
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ Commute Delay"
          message: >
            Your train may be delayed. Check before leaving!
```

## Delay Check Service Automation

### Periodic Delay Check with Notification

Use the `check_delays` service to periodically scan for delays and get notified via the fired event.

```yaml
automation:
  - alias: "Check delays every 10 minutes"
    trigger:
      - platform: time_pattern
        minutes: "/10"
    condition:
      - condition: time
        after: "06:00:00"
        before: "22:00:00"
    action:
      - service: openpublictransport.check_delays
        data:
          entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
          delay_threshold: 5

  - alias: "Notify on delay alert event"
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
            {{ trigger.event.data.delayed_count }} delayed departure(s) at your stop.
            Max delay: {{ trigger.event.data.max_delay }} min.
            Affected lines: {{ trigger.event.data.lines | join(', ') }}
```

## TTS Departure Announcement

### Morning TTS Announcement via announce_departure

Use the `announce_departure` service to get a ready-made spoken text and pass it to any TTS engine.

```yaml
automation:
  - alias: "TTS departure announcement"
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

## Departure Reminders

### Remind to Leave

Remind you when it's time to leave for the station.

```yaml
automation:
  - alias: "Time to leave reminder"
    trigger:
      - platform: template
        value_template: >
          {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'next_departure_minutes') | int <= 15 }}
    condition:
      - condition: state
        entity_id: person.john
        state: home
    action:
      - service: notify.mobile_app
        data:
          title: "Time to Leave!"
          message: >
            Your train leaves in {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'next_departure_minutes') }} minutes.
            Line: {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'departures')[0].line }}
```

### Smart Departure Alert

Factor in walking time to the station.

```yaml
automation:
  - alias: "Smart departure alert"
    trigger:
      - platform: template
        value_template: >
          {% set walk_time = 10 %}
          {% set buffer = 5 %}
          {% set mins = state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'next_departure_minutes') | int %}
          {{ mins <= (walk_time + buffer) and mins > 0 }}
    condition:
      - condition: state
        entity_id: person.john
        state: home
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: notify.mobile_app
        data:
          title: "🚉 Leave Now!"
          message: >
            Train departs in {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'next_departure_minutes') }} min.
            {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'departures')[0].line }} →
            {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'departures')[0].destination }}
```

## Display Automations

### Show Departure on Smart Display

Update a smart display or tablet with departure info.

```yaml
automation:
  - alias: "Update departure display"
    trigger:
      - platform: state
        entity_id: sensor.openpublictransport_dusseldorf_hauptbahnhof
    action:
      - service: input_text.set_value
        target:
          entity_id: input_text.next_departure
        data:
          value: >
            {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'departures')[0].line }} at
            {{ states('sensor.openpublictransport_dusseldorf_hauptbahnhof') }}
```

### TTS Announcement

Announce the next departure via text-to-speech.

```yaml
automation:
  - alias: "Announce next departure"
    trigger:
      - platform: time
        at: "07:30:00"
    condition:
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: tts.speak
        target:
          entity_id: tts.google_translate
        data:
          message: >
            {% set dep = state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'departures')[0] %}
            Your next train is line {{ dep.line }} to {{ dep.destination }}
            departing at {{ dep.departure_time }}{% if dep.delay > 0 %}, delayed by {{ dep.delay }} minutes{% endif %}.
```

## Template Sensors for Automations

Create helper sensors for easier automations.

```yaml
template:
  - sensor:
      - name: "Next Train Minutes"
        state: >
          {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'next_departure_minutes') }}
        unit_of_measurement: "min"
        icon: mdi:clock-outline

      - name: "Next Train Line"
        state: >
          {% set departures = state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'departures') %}
          {% if departures and departures|length > 0 %}
            {{ departures[0].line }}
          {% else %}
            -
          {% endif %}
        icon: mdi:train

      - name: "Next Train Destination"
        state: >
          {% set departures = state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'departures') %}
          {% if departures and departures|length > 0 %}
            {{ departures[0].destination }}
          {% else %}
            -
          {% endif %}
        icon: mdi:map-marker

      - name: "Train Status"
        state: >
          {% if is_state('binary_sensor.openpublictransport_dusseldorf_hauptbahnhof_delays', 'on') %}
            Delayed
          {% else %}
            On Time
          {% endif %}
        icon: >
          {% if is_state('binary_sensor.openpublictransport_dusseldorf_hauptbahnhof_delays', 'on') %}
            mdi:alert-circle
          {% else %}
            mdi:check-circle
          {% endif %}
```

## Scripts

### Departure Info Script

A reusable script to get departure information.

```yaml
script:
  get_next_departure:
    alias: "Get Next Departure"
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
            {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'departures')[0].line }} →
            {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'departures')[0].destination }}
            at {{ states('sensor.openpublictransport_dusseldorf_hauptbahnhof') }}
            (in {{ state_attr('sensor.openpublictransport_dusseldorf_hauptbahnhof', 'next_departure_minutes') }} min)
```
