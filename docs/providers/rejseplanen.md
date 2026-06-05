# Rejseplanen (Denmark)

!!! info "API Key Required"
    Rejseplanen uses a RESTful HAFAS API. A free API key is required for non-commercial use — register at [labs.rejseplanen.dk](https://labs.rejseplanen.dk) (50,000 calls/month).

## Coverage Area

All public transport in Denmark:

- **S-tog** — Copenhagen suburban rail (lines A–H)
- **Metro** — Copenhagen Metro (M1, M2, M3 Cityringen, M4 Orientkaj)
- **IC / Intercity** — Long-distance trains (DSB)
- **Regional trains** — RE/REG services across Denmark
- **Bus** — City and regional buses
- **Express bus (EXB)** — Long-distance express buses
- **Ferry (F / Færge)** — Domestic ferry connections
- **Tram (T)** — Aarhus Letbane (Odder–Grenaa)

## API Details

| Property | Value |
|----------|-------|
| **Endpoint** | `https://www.rejseplanen.dk/api/` |
| **API Type** | HAFAS REST (JSON) |
| **API Key** | Required (free, 50k calls/month) |
| **Timezone** | Europe/Copenhagen |
| **Realtime** | Yes — live delays and cancellations |

## Getting an API Key

1. Go to [labs.rejseplanen.dk](https://labs.rejseplanen.dk)
2. Click **"Anmod om adgang"** (Request access)
3. Fill in the form — select **RESTful API** and non-commercial use
4. You will receive credentials by email (usually within a few days)
5. Enter the API key during integration setup

!!! tip
    The free tier covers 50,000 API calls per month — sufficient for typical personal Home Assistant use (1 sensor polling every 60 seconds = ~43,000 calls/month).

## Configuration

### Setup Steps

1. In Home Assistant, go to **Settings → Integrations → Add Integration**
2. Search for *Public Transport Departures*
3. Select **Entry Type**: Abfahrtsanzeige / Departure Monitor
4. Select **Provider**: `Rejseplanen — Dänemark (API Key)`
5. Enter your Rejseplanen API key
6. Search for your stop (see tips below)
7. Configure departure count and scan interval

### Stop Search Tips

Search by station name — Danish, English, or partial names all work:

| What you type | What it finds |
|---------------|---------------|
| `Aarhus H` | Aarhus Hoved­banegård |
| `Kobenhavn H` | København H (Central Station) |
| `Norreport` | Nørreport St |
| `Odense` | Odense St |
| `Kastrup` | København Lufthavn Kastrup |

!!! tip
    Danish characters (Æ, Ø, Å) work correctly. You can also search without them — "Kobenhavn" finds "København".

## Transport Types

| Rejseplanen Type | Description | Unified Type |
|-----------------|-------------|--------------|
| IC | Intercity (DSB) | train |
| RE / REG | Regional train | train |
| S | S-tog (Copenhagen suburban) | train |
| TOG | Generic train | train |
| M | Metro (Copenhagen) | subway |
| BUS | City/regional bus | bus |
| EXB | Express bus | bus |
| NB | Night bus | bus |
| F | Ferry (Færge) | ferry |
| T | Tram (Aarhus Letbane) | tram |

## Realtime Data

Rejseplanen's API includes live data from DSB and other operators:

- Real-time departure times with delay in minutes
- Platform changes (track changes at the last moment)
- Cancellations with reason text
- Service disruption notices

## Troubleshooting

### HTTP 401 / Unauthorized

Your API key is invalid or expired. Re-register at [labs.rejseplanen.dk](https://labs.rejseplanen.dk).

### No stops found

- Try different spelling (e.g., "Nørreport" instead of "Norreport", or vice versa)
- Use the main station name without street/district suffix
- Try just the city name to see all stations in that city

### No departures shown

- Verify the stop has service at the current time (some rural stops have limited hours)
- Check if your scan interval is frequent enough
- Enable debug logging: `custom_components.openpublictransport: debug`
