# National Rail (UK)

National Rail provides live departure information for all rail services across
Great Britain via the **OpenLDBWS** (Live Departure Boards Web Service) — the
public interface to *Darwin*, National Rail's realtime data feed.

## Coverage Area

- All National Rail services across Great Britain
- Long-distance operators (LNER, GWR, Avanti West Coast, CrossCountry, …)
- Regional and commuter services
- Eurostar (via domestic stops)

## API Details

| Property | Value |
|----------|-------|
| **Endpoint** | `https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx` |
| **Protocol** | SOAP / XML |
| **API Key** | Required (free, 100k calls/month) |
| **Timezone** | Europe/London |
| **Transport Types** | Train only |

## Getting a Token (Rail Data Marketplace)

!!! warning "The old registration portal is gone"
    OpenLDBWS tokens used to be self-issued at `realtime.nationalrail.co.uk`.
    That portal (and the National Rail Data Portal, `opendata.nationalrail.co.uk`)
    was **retired in early 2026**. New tokens are now issued through the
    **Rail Data Marketplace (RDM)** at [raildata.org.uk](https://raildata.org.uk/).
    Existing, still-valid tokens continue to work in the meantime.

The token you need is called a **Consumer key** on RDM, and you get it by
*subscribing to a product* — there is no standalone "create key" button.

1. Create an account and sign in at [raildata.org.uk](https://raildata.org.uk/).
2. Open the **Data Product Catalogue** and search for **LDBWS**.
3. Subscribe to **"Live Departure Board Web Service (LDBWS) - Public"** and accept
   the licence (the free, open tier is approved instantly).
    - ⚠️ Do **not** pick *Live Fastest Departure Boards* (a different REST product)
      or the *Staff Version* — this integration talks to the classic SOAP service.
4. Go to your dashboard → **My Subscriptions** and open the subscribed product.
5. On the **Specification / API** tab, copy the **Consumer key** — that string is
   your OpenLDBWS access token.
6. Enter it during integration setup.

!!! tip
    The free tier allows 100,000 calls per month — far more than enough for
    personal Home Assistant use.

!!! note "Not based in the UK?"
    Registration for the *LDBWS - Public* product does not have a documented
    UK-residency requirement, but the sign-up form is aimed at UK organisations.
    If you cannot complete registration, a valid Consumer key issued to anyone
    works in the token field regardless of where it was created. If you hit a
    hard block, ask on the [Open Rail Data community](https://groups.google.com/g/openraildata-talk).

## Configuration

### Setup Steps

1. Select **National Rail — UK** as the provider.
2. Enter your OpenLDBWS Consumer key.
3. Search for your station (see below).
4. Select from the results and configure the departure count.

### Station Search

Station search uses the **Overpass API** (OpenStreetMap) to find UK railway
stations and their 3-letter **CRS** codes — it does **not** consume your token.
You can search two ways:

| What you type | What it finds |
|---------------|---------------|
| `kings cross` | London King's Cross (KGX) |
| `leeds` | Leeds (LDS) |
| `manchester piccadilly` | Manchester Piccadilly (MAN) |
| `WIN` | Winchester (WIN) — direct CRS code lookup |
| `RDG` | Reading (RDG) — direct CRS code lookup |

Anything that is exactly three letters is treated as a **CRS code** and matched
directly; longer terms are matched against the station name (case-insensitive,
partial). Direct CRS-code search requires **integration v2026.7.1 or newer**.

!!! tip
    If a name is ambiguous, add the city (e.g. `Manchester Piccadilly` rather
    than `Piccadilly`).

## Transport Types

National Rail is a **train-only** provider — every departure is classified as
`train`. The line badge shows the operator's 2-letter code:

| Code | Operator |
|------|----------|
| GR | LNER |
| GW | Great Western Railway |
| VT | Avanti West Coast |
| SW | South Western Railway |
| SN | Southern |
| LM | West Midlands Trains |
| XC | CrossCountry |
| EM | East Midlands Railway |

## Realtime Data

OpenLDBWS delivers live data straight from Darwin:

- **On time** — no delay, realtime confirmed
- **HH:MM** — estimated departure time (delay calculated in minutes)
- **Delayed** — delay confirmed but no estimate yet
- **Cancelled** — service cancelled (with reason if available)

## Troubleshooting

### No results in station search

- Search by the station **name** (`Winchester`, `Reading`) **or** by its
  **3-letter CRS code** (`WIN`, `RDG`). Direct code search needs v2026.7.1+.
- The station must be a CRS-tagged UK railway station in OpenStreetMap.
- If a partial name is ambiguous, add the city name to narrow it down.

### HTTP 401 / 403 — authentication failed

Your Consumer key is missing, invalid, or the subscription lapsed. Re-check it
in your [Rail Data Marketplace](https://raildata.org.uk/) subscription
(**My Subscriptions → LDBWS - Public → Specification → Consumer key**).

### Occasional maintenance windows

OpenLDBWS may have brief outages around 02:00–05:00 UK time. If queries fail
then, retry after a few minutes.
