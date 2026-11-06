# Public Marquez Web — current component overview

**Live-facing component:** Public-only Marquez 0.51.1 Web overlay in [`platform-portal/portal/web/`](../../../../platform-portal/portal/web/). It is an independent UI/image from the private, official LAN Marquez Web and does not grant API or dataset permissions.

## Verified user experience (2026-11-05)

- Public root [`lineage.johnzhang-dataforge.site`](https://lineage.johnzhang-dataforge.site/) keeps the original Marquez Dashboard. Datasets select populated `s3://health-landing` while Jobs independently select populated `healthcare-platform-airflow`, preserving visitor choices.
- A public-only overlay performs at most one native Empty State Refresh where the correctly selected list reports `0 total`. No fabricated data, direct unapproved API read, or polling loop is added.
- [Browser verification Run #41965389280](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41965389280) completed in actual Chromium and WebKit mobile-sized contexts: Dashboard → 3 Landing datasets → 10 Airflow jobs → 3 Landing datasets without a visitor refresh. Physical iPhone in-app Safari and stale browser cache are not automatically covered.
- Deployed immutable [GHCR image rollout Run #41964675838](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41964675838) verified the pinned digest. This does not imply that the existing internal Marquez API is public-writeable.

## Ownership and safety

- [Dedicated public Web implementation](../../../../platform-portal/portal/web/), [LAN isolation manifest](../../../../platform-portal/portal/web/kubernetes/lan.yaml), and [Portal CODE](CODE.md).
- UI element hiding is only presentation. Gateway/proxy must independently deny write methods, unauthorized endpoints and sensitive GETs. Secrets, internal host details, PG14 and backend authorization never belong in the public JavaScript overlay.
- Tests: `node --test platform-portal/portal/web/tests/*.test.cjs`; candidate build: `docker build -t healthcare-portal-public-web:test platform-portal/portal/web`. Neither command authorizes push or deployment. Cluster/Tunnel/Service changes need a separately authorized scope.
- [Implementation and acceptance history](PUBLIC-MARQUEZ-WEB-HISTORY-20261105.md) preserves the prior source-root README with exact dates, historical failures, fallback behavior and release evidence, rather than repeating a chronological diary in this current overview.
