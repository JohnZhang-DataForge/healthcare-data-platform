---
status: active
scope: platform-portal-public-interface
last_verified: 2026-11-05
---

# Portal — Public Marquez UI, Exporter and Future Control

Human-facing component navigation. Actual source in [portal source](../../../../platform-portal/portal/) and [CODE map](CODE.md). This subsystem does not own PG14/PG17 transactions or Cloudflare administration.

| Area | Primary guidance | Acceptance boundary |
| --- | --- | --- |
| Public Marquez Web | [Current overview](PUBLIC-MARQUEZ-WEB.md) · [full implementation history](PUBLIC-MARQUEZ-WEB-HISTORY-20261105.md) | Independent browser readback passed; keep gateway write methods blocked |
| Marquez Exporter | [Exporter design, tests and safety](MARQUEZ-EXPORTER.md) | Offline sanitized GET-only tool; real export/public promotion separately reviewed |
| OpenLineage relay | [Blob Relay guide](../BLOB-RELAY.md) | Offline/injected interface, no unapproved private Marquez POST |
| Portal Control & Cloudflare | [Original P0 contract record](PORTAL-P0-HISTORY-20261105.md) · [Cloudflare Manual](CLOUDFLARE-MANUAL.md) | P0 mock/contract is not evidence a paid worker/control plane is deployed |

**Safety:** UI hiding is not authorization. Real public data must have reviewed source Manifest/Run/SHA; simulated records require visible MOCK labeling. Future interactive or paid-resource actions need approved design, budget and access gates. Track business progress in [active Portal OpenSpec](../../../../openspec/changes/healthcare-on-demand-live-demo/tasks.md), not this README.

The [original P0 narrative](PORTAL-P0-HISTORY-20261105.md) preserves all contract names, old decisions, historical failures and PR/Run evidence at its original relative link depth. It is not a current deployment report.
