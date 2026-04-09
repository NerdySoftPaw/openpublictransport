# AVV (Augsburger Verkehrs- & Tarifverbund)

AVV is the transit authority for the Augsburg region in Bavaria, Germany.

!!! note "Provider ID"
    This provider uses `avv_augsburg` as its internal ID to distinguish it from other AVV-named networks.

## Coverage Area

- Augsburg
- Augsburg metropolitan area

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://fahrtauskunft.avv-augsburg.de/efa/` |
| **API Type** | EFA |
| **API Key** | Not required |
| **Timezone** | Europe/Berlin |

## Transport Types

| Class | Type | Description |
|-------|------|-------------|
| 0 | train | High-speed trains (ICE, IC, EC) |
| 1 | train | Regional trains (RE, RB, S-Bahn) |
| 4 | tram | Tram |
| 5-8 | bus | Bus services |
| 13 | train | Regional (RE) |

## Setup Steps

1. Select **AVV (Augsburg)** as provider
2. Search for your stop (e.g., "Königsplatz")
3. Select the stop from the list
4. Configure departure count and filters

## Example Stops

- Augsburg Hauptbahnhof
- Augsburg Königsplatz
- Augsburg Moritzplatz
- Augsburg Rathausplatz
