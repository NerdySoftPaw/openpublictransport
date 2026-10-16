# Migration Guide

The full migration guide is now part of the documentation:

**[docs.openpublictransport.net/migration](https://docs.openpublictransport.net/migration/)**

Three migrations exist:

1. **VRRAPI-HACS → hacs-publictransport** — Repo rename only, domain stayed `vrr`, no breaking change
2. **hacs-publictransport → openpublictransport** — Domain changed from `vrr` to `openpublictransport`, all entity IDs and services renamed (breaking change)
3. **openpublictransport provider → self-hosted OTP2** (v2026.10.0) — The hosted community server `api.openpublictransport.net` was shut down for cost reasons; entries using it are removed on update. Re-add your stops with the official provider of your transit network, or with the **OTP2 — Eigene Instanz** provider pointing at your own OTP2 server. Background: [Community Server Shutdown & Our New Focus](https://docs.openpublictransport.net/community-server-shutdown/)
