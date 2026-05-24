# OTP2 Custom Instance

The `otp_custom` provider lets you connect any self-hosted [OpenTripPlanner 2](https://www.opentripplanner.org/) server to Home Assistant. This is useful if you run your own OTP2 instance — for example a local gtfs.de deployment, a private GTFS feed, or the community server image on your own hardware.

## When to Use This

| Scenario | Provider to Use |
|----------|----------------|
| You want Germany-wide data, no hassle | [openpublictransport](openpublictransport.md) (community server) |
| You run your own OTP2 with gtfs.de data | **otp_custom** → point at your server |
| You have a private/local GTFS feed in OTP2 | **otp_custom** |
| You self-host the community server image | **otp_custom** |

## API Details

| Property | Value |
|----------|-------|
| **Server** | Your own URL |
| **API Type** | OTP2 GraphQL |
| **API Key** | Optional (X-API-Key header) |
| **Timezone** | Europe/Berlin (configurable via OTP2) |

## Configuration

### Setup Steps

1. In Home Assistant, go to **Settings → Integrations → Add Integration**
2. Search for *Public Transport Departures*
3. Select **Entry Type**: Abfahrtsanzeige / Departure Monitor
4. Select **Provider**: `OTP2 — Eigene Instanz (URL + optionaler API Key)`
5. Enter your **OTP2 Base URL** — include the router path:
   ```
   http://192.168.1.10:8080/otp/routers/default
   ```
6. Enter an **API Key** if your server requires one (leave blank otherwise)
7. Search for your stop and finish configuration

### URL Format

The base URL must point to the OTP2 router, not just the server root:

| Setup | Correct URL |
|-------|-------------|
| Local OTP2 (default port) | `http://192.168.1.10:8080/otp/routers/default` |
| Reverse proxy without path | `https://otp.yourdomain.com/otp/routers/default` |
| Reverse proxy with subpath | `https://yourdomain.com/otp/otp/routers/default` |
| Community server image (self-hosted) | `https://your-vps.example.com/otp/routers/default` |

The integration appends `/index/graphql` to this URL for all requests.

## Self-Hosting with gtfs.de

The easiest way to run your own server is the community Docker image:

```bash
# Clone the repo
git clone https://github.com/NerdySoftPaw/otp-gtfsde
cd otp-gtfsde

# Start (downloads GTFS, builds graph, starts OTP2)
docker compose up -d
```

The graph build takes 15–30 minutes on first start. After that, the server is available at `http://localhost:8080` and the GTFS data is refreshed daily.

**Minimum requirements:**

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 6 GB | 8 GB |
| CPU | 2 cores | 4 cores |
| Storage | 15 GB | 20 GB |

See the [otp-gtfsde repository](https://github.com/NerdySoftPaw/otp-gtfsde) for full configuration, nginx reverse proxy setup, and API key authentication.

## Transport Types

Same as the community server — all OTP2 GTFS modes are supported:

| OTP2 Mode | Type |
|-----------|------|
| RAIL | train |
| SUBWAY | subway |
| TRAM | tram |
| BUS | bus |
| FERRY | ferry |
| COACH | bus |

## Features

- **Full city-prefix search** — same VRR/NRW prefix logic as the community server
- **Multi-platform merging** — stops grouped by name, platforms fetched in parallel
- **Optional API key** — `X-API-Key` header sent when configured
- **GTFS-RT** — realtime delays if your OTP2 instance is configured with a GTFS-RT updater

## Troubleshooting

### Connection Refused / Timeout

- Check that OTP2 is running: `curl http://localhost:8080/otp/routers/default/index/graphql -X POST -H "Content-Type: application/json" -d '{"query":"{ stops(name: \"Hbf\") { gtfsId name } }"}'`
- Verify the port is correct and not blocked by a firewall
- If using a reverse proxy, check the nginx/Caddy configuration

### GraphQL Errors

- Verify your OTP2 version supports the GraphQL endpoint (OTP2 2.x required)
- The legacy REST API (`/otp/routers/default/index/stops`) is not used — only GraphQL
- Check OTP2 logs for query errors

### No Stops Found

- Confirm the graph was built with your GTFS feed
- Test the GraphQL endpoint directly with a known stop name
- Graph build may still be in progress (check OTP2 logs)
