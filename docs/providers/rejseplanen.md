# Rejseplanen (Denmark)

Rejseplanen is the national journey planner for Denmark. It covers every operator
in the country — DSB, Arriva, the Copenhagen Metro, regional buses and ferries —
through a HAFAS REST API.

## Coverage Area

- All of Denmark, nationwide
- National and regional rail (DSB, Arriva)
- Copenhagen Metro and S-tog
- Regional and city buses
- Domestic ferries

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://www.rejseplanen.dk/api` |
| **API Type** | HAFAS REST |
| **API Key** | Required (free) |
| **Timezone** | Europe/Copenhagen |

## Getting an API Key

1. Register at [labs.rejseplanen.dk](https://labs.rejseplanen.dk/).
2. Request access to the Rejseplanen API.
3. You receive an access ID, which the integration sends as `accessId`.

The free tier allows **50,000 calls per month** and is limited to non-commercial
use. At the default scan interval of 60 seconds, one departure sensor uses roughly
44,000 calls per month — so plan on one sensor per key, or raise the scan interval
when you configure several.

## Transport Types

Rejseplanen reports the product category (`catOut`), which maps as follows:

| Category | Type | Description |
|----------|------|-------------|
| IC, LYN | train | InterCity and InterCityLyn long-distance trains |
| RE, REG, TOG | train | Regional trains |
| S | train | S-tog (Copenhagen suburban rail) |
| M | subway | Copenhagen Metro |
| BUS, EXB, NB, TB | bus | City, express, night and rail-replacement buses |
| T | tram | Aarhus and Odense light rail |
| F | ferry | Ferries |

## Configuration

### Setup Steps

1. Select **Rejseplanen** as provider
2. Enter your API key
3. Search for your stop (e.g., "København H")
4. Select the stop from the list
5. Choose transport types and the number of departures

### Example Stops

- `København H`
- `Aarhus H`
- `Odense St.`
- `Nørreport St.`

## Special Features

### Real-Time Data

Departures carry both the planned and the live time, so delays show up directly.
Platform changes are detected by comparing the real-time track against the
scheduled one.

### Cancellations

Cancelled departures are flagged and reported in the departure attributes.

## Limitations

- Trip planning is not available for this provider.
- The API key is personal — keep it out of shared dashboards and screenshots.
