# mobilitéit.lu (Luxembourg)

Luxembourg's national multimodal journey planner (train, bus and tram) via the legacy HAFAS "Scotty" web interface.

## Coverage Area

- All of Luxembourg
- CFL national and regional rail
- RGTR / TICE / AVL bus networks
- Luxembourg tram
- Cross-border regional trains (e.g. TER to France)

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://cdt.hafas.de/bin` |
| **API Key** | Not required |
| **Timezone** | Europe/Luxembourg |
| **Data Format** | HAFAS Scotty (`ajax-getstop.exe` + `stboard.exe`) |

## Transport Types

| Category | Type | Description |
|----------|------|-------------|
| RB / RE | train | Regional trains |
| TER | train | Cross-border regional express (FR) |
| IC / EC | train | Long-distance |
| Bus | bus | RGTR / TICE / AVL buses |
| Tram | tram | Luxembourg tram |

## Configuration

### Setup Steps

1. Select **mobilitéit.lu -- Luxemburg** as provider
2. Search for your stop (e.g. "Luxembourg, Gare Centrale")
3. Select the stop from the list
4. Configure departure count and filters

### Example Stops

- Luxembourg, Gare Centrale
- Esch-sur-Alzette, Gare
- Ettelbruck, Gare
- Luxembourg, Hamilius

## Features

- Realtime departure data with delay in minutes
- Platform information with change detection
- Service disruption notices (HIM messages)
- No API key required
