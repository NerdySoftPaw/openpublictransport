# Community Server Shutdown & Our New Focus

!!! warning "The openpublictransport community server has been shut down"
    As of **v2026.10.0**, the hosted OTP2 server at `api.openpublictransport.net` is no longer
    operated, and the `openpublictransport` provider has been removed from the integration.
    Everything else keeps working exactly as before.

## TL;DR

- We had to give up our own API at `api.openpublictransport.net` — **purely for cost reasons**.
- Entries that used the `openpublictransport` provider are **removed automatically** when you
  update to v2026.10.0. A repair notice in Home Assistant tells you which ones.
- **All other providers are unaffected.** If your stops use VRR, KVV, MVV, DB, Transitous or
  any other provider, nothing changes for you.
- You can keep Germany-wide GTFS.DE data by **hosting the same server yourself** and connecting
  it with the **OTP2 Custom** provider.
- From now on, development focuses on **connecting more transit networks (Verkehrsverbünde)
  directly** through their official interfaces.

---

## Why We Shut Down Our Own API

When we launched the community server, the goal was simple: one API key, Germany-wide
real-time departures and trip planning for every Home Assistant user, without having to find
out which transit network covers your stop.

Technically this worked well. Financially, it did not. Running a Germany-wide OpenTripPlanner 2
instance is expensive:

- **Server resources** — OTP2 keeps the full routing graph for all of Germany in memory. That
  needs a large, dedicated machine that runs 24/7, no matter how many people use it at a given
  moment.
- **Weekly graph rebuilds** — the timetable data from gtfs.de changes constantly. Every Sunday
  the complete graph was rebuilt from scratch, which needs even more memory and CPU for the
  duration of the build.
- **Real-time data** — the server polled the GTFS-RT feed every 30 seconds around the clock and
  merged it into the graph.
- **Traffic, storage, backups and monitoring** — all of which grow with every new user.

The project is a free, open-source hobby project. There is no company behind it, and every
cost of the community server was paid out of pocket. Donations helped and we are genuinely
grateful for every single one — but they never came close to covering the running costs, and
the gap kept growing as more people started using the server.

We did look for alternatives — smaller machines, a reduced coverage area, stricter rate
limits — but each of them would have made the service either unreliable or no longer
"Germany-wide", which was the whole point of it. Rather than offering a service that slowly
degrades, we decided to shut it down cleanly and say so openly.

**This decision was not made lightly.** We know that many of you set up your dashboards and
automations on top of the community server, and we are sorry for the extra work this causes.

---

## What Happens When You Update

On the first start after updating to **v2026.10.0**:

1. Every config entry that uses the `openpublictransport` provider — departure boards **and**
   trip planners — is deleted, together with its devices and entities. Those entries could never
   load again, because the server behind them no longer exists.
2. A repair notice appears under **Settings → System → Repairs** and lists the removed entries
   by name, so you know exactly what to set up again. Confirm it to dismiss it.
3. Dashboards, automations and scripts that referenced the removed entities will show them as
   unavailable until you point them at the replacement entities.

Entries of every other provider are **not touched**.

---

## Your Options

### Option 1: Use the official provider of your transit network (recommended)

For most people this is the best replacement. These providers talk directly to the official
interfaces of the transit networks, need no server of your own and usually deliver the most
accurate real-time data for their region.

Germany is already covered by a large number of networks:

| Region | Provider |
|--------|----------|
| Rhein-Ruhr (NRW) | [VRR](providers/vrr.md) |
| Westfalen-Lippe | [NWL](providers/nwl.md) |
| Karlsruhe | [KVV](providers/kvv.md) |
| Baden-Württemberg | [NVBW](providers/nvbw.md) |
| Stuttgart | [VVS](providers/vvs.md) |
| Freiburg | [VAG](providers/vagfr.md) |
| Ulm / Donau-Iller | [DING](providers/ding.md) |
| Rhein-Neckar | [VRN](providers/vrn.md) |
| Frankfurt / Rhein-Main | [RMV](providers/rmv.md) |
| München | [MVV](providers/mvv.md) |
| Bayern | [BEG](providers/beg.md) |
| Nürnberg | [VGN](providers/vgn.md) |
| Augsburg | [AVV](providers/avv.md) |
| Regensburg | [RVV](providers/rvv.md) |
| Hamburg | [HVV](providers/hvv.md), [HVV Geofox GTI](providers/hvv-gti.md) |
| Bremen / Niedersachsen | [VBN](providers/vbn.md) |
| Braunschweig | [BSVG](providers/bsvg.md) |
| Berlin / Brandenburg | [BVG](providers/bvg.md) |
| Dresden | [VVO](providers/vvo.md) |
| Germany-wide (long-distance and regional rail) | [DB](providers/db.md) |

Outside of these regions, [Transitous](providers/transitous.md) offers worldwide coverage from
aggregated open data. See the [provider overview](providers/index.md) for all providers,
including those outside Germany.

### Option 2: Host the community server yourself

The server we ran is open source. You can run exactly the same setup on your own hardware with
the [`otp-gtfsde`](https://github.com/NerdySoftPaw/otp-gtfsde) Docker image and connect it with
the **OTP2 — Eigene Instanz** (`otp_custom`) provider. You keep Germany-wide GTFS.DE data,
trip planning and the automatic city-prefix search.

Be aware that a Germany-wide graph needs a machine with plenty of memory — the very reason we
could no longer afford to run it for everyone. A graph limited to your own region is much
lighter. See [OTP2 Custom Instance](providers/otp-custom.md#self-hosting-with-gtfsde) for the
setup guide.

### Setting your stops up again

1. Go to **Settings → Devices & Services → Add Integration → openpublictransport**.
2. Pick the provider from option 1 or 2.
3. Search and select your stops as before.
4. Update dashboards and automations to the new entity IDs.

The [Migration Guide](migration.md#migration-3-openpublictransport-provider-self-hosted-otp2-v2026100)
has the same steps in short form.

---

## Our New Focus: More Transit Networks

Shutting down the community server also clarifies where this project goes next. Instead of
running central infrastructure ourselves, we are now **fully focused on connecting more transit
networks (Verkehrsverbünde) directly** — in Germany and beyond.

This approach is better for everyone:

- **Official data, straight from the source.** Every network's own interface knows its
  timetable, delays, platform changes and disruptions best — often better than any aggregated
  feed.
- **No central server, no running costs.** Your Home Assistant talks directly to the transit
  network. Nothing depends on a server we would have to pay for and keep alive.
- **No single point of failure.** If one network has an outage, every other provider keeps
  working. There is no weekly maintenance window that takes everything offline at once.
- **It scales.** Every new provider helps everyone in that region forever, without adding a
  single cent of hosting costs.

The integration already supports many networks through shared building blocks (EFA, TRIAS,
HAFAS, OTP and more). Every network that uses one of these systems can be added with
comparatively little effort — and many German networks do.

### How you can help

- **Request your network.** Open a
  [Provider Request](https://github.com/NerdySoftPaw/openpublictransport/issues/new?template=provider_request.yml)
  and tell us which network you need. Links to an API, open-data portal or developer
  documentation speed things up enormously.
- **Test new providers.** New providers are released as beta first. Feedback from people who
  actually ride those lines is the most valuable test there is.
- **Report data issues.** If a provider shows wrong lines, platforms or delays, a
  [Provider Data Issue](https://github.com/NerdySoftPaw/openpublictransport/issues/new?template=provider_data_issue.yml)
  helps us fix it.
- **Support the project.** If you want to support the work on new providers, you can do so via
  [Buy Me a Coffee](https://buymeacoffee.com/nerdysoftpaw) or [Ko-fi](https://ko-fi.com/nerdysoftpaw90).

---

## Thank You

To everyone who requested an API key, reported bugs, tested the community server and helped
make it better: **thank you.** The server is gone, but everything we learned from it — the
city-prefix search, the compound stop IDs, the OTP2 trip planning — lives on in the integration
and in the self-hostable image.

Questions? Ask in the
[GitHub Discussions](https://github.com/NerdySoftPaw/openpublictransport/discussions/categories/q-a).
