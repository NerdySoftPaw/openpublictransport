# HVV Geofox GTI (Hamburg, official API)

The **Geofox Thin Interface (GTI)** is HOCHBAHN's official API, operated on behalf of the
Hamburger Verkehrsverbund. It is an alternative to the keyless [HVV](hvv.md) provider, which
uses the public EFA endpoint.

Both providers stay available. Pick this one if you want real-time data; pick the plain
[HVV](hvv.md) provider if you do not want to apply for credentials.

!!! note
    "hvv" is the *Hamburger Verkehrsverbund*, the regional transit association. HOCHBAHN is a
    company within it and runs the API on the association's behalf.

## Why use it

| | HVV (EFA) | HVV Geofox GTI |
|---|---|---|
| Credentials | none | username + password, free |
| Real-time delays | inferred from planned vs. estimated | explicit `delay` in seconds |
| Cancellations | ✗ | ✓ |
| Platform changes | ✗ | ✓ (`realtimePlatform`) |
| Reinforcement trips (*Verstärkerfahrten*) | ✗ | ✓ |

## Getting credentials

The API is **free**. Send an email to **api@hochbahn.de** describing your project and naming a
contact person. You receive a username (the *application ID*) and a password.

See [hvv.de — Datenabruf](https://www.hvv.de/de/fahrplaene/abruf-fahrplaninfos/datenabruf) and
the [GTI handbook](https://gti.geofox.de/html/GTIHandbuch_p.html).

!!! warning "Terms of use"
    HOCHBAHN grants access for building a **free-of-charge** travel information service. You
    may not charge for it directly or indirectly, and you may not pass the data on to third
    parties without written approval. Access can be withdrawn with four weeks' notice. Running
    this integration in your own Home Assistant is exactly the intended use; republishing the
    data is not.

## API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://gti.geofox.de/gti/public/` |
| **API version** | 63 |
| **Credentials** | Required (username + password) |
| **Authentication** | HMAC-SHA1 over the request body, Base64, in `geofox-auth-signature` |
| **Timezone** | Europe/Berlin |
| **Methods used** | `checkName` (stop search), `departureList` (departures) |

Your password is used as the HMAC key to sign each request — it is never sent to the server.
Both values are stored in Home Assistant's **Application Credentials** store, like every other
provider key.

## Configuration

1. Select **HVV — Hamburg (Geofox GTI, Zugangsdaten)** as provider
2. Enter your GTI username and password
3. Search for your stop (e.g. "Hamburg Hauptbahnhof")
4. Select the stop and configure departure count and filters

Once entered, the credentials are reused automatically for any further GTI entries.

## Transport Types

Mapped from the line's `type.shortInfo`, falling back to the coarse `type.simpleType` and,
where that is ambiguous, to the line name.

| GTI | Type |
|-----|------|
| `UBAHN` / `U` | subway |
| `SBAHN` / `S`, `AKN` / `A`, `RBAHN`, `FERNBAHN`, `ZUG` | train |
| `BUS`, `STADTBUS`, `METROBUS`, `SCHNELLBUS`, `NACHTBUS`, `XPRESSBUS`, `EILBUS` | bus |
| `FAEHRE` / `SHIP` | ferry |
| `AST` (Anruf-Sammel-Taxi) | taxi |

## Departure attributes

GTI returns offsets rather than timestamps: a reference time for the whole board, plus per
departure a `timeOffset` in **minutes** and a `delay` in **seconds**.

- `planned_time` = reference + `timeOffset`
- `departure_time` = `planned_time` + `delay`
- `delay` is reported in minutes, as for every other provider
- `platform` prefers `realtimePlatform` over the scheduled `platform`; when the two differ,
  `platform_changed` is set and the disruption event entity fires
- cancellations and reinforcement trips appear in `notices`

## Limitations

- **Trip planning is not supported yet.** The GTI `getRoute` method is not wired up; use the
  keyless [HVV](hvv.md) provider for trip entries.
- The public interface is limited to HVV lines.
