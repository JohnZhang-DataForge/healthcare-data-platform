# Public read-only Marquez Web

Source of the public UI overlay and dedicated image, derived from official Marquez Web 0.51.1 (Apache-2.0, digest pinned). Original private LAN Web is unchanged. No local tunnel, gateway configuration, credentials, network addresses or real metadata are stored here.

The public variant hides Delete Job/Dataset, Edit Tag, Tag Submit/deletion, Tag editing input and raw Events navigation (currently denied by Gateway). Dashboard, Jobs, Datasets, Run History, Table/Column Lineage, filters, refresh, zoom and navigation stay available.

**UI hiding is not authorization.** A visitor can bypass browser JavaScript. Gateway must still reject all writing methods and unapproved endpoints and sensitive GET content must be reviewed.

Test: node --test platform-portal/portal/web/tests/*.test.cjs

Build: docker build -t healthcare-portal-public-web:test platform-portal/portal/web

CI builds on PR without publishing; Main push/dispatch publishes ghcr.io/johnzhang-dataforge/healthcare-portal-public-web:sha-<commit>.

Deploy this independently to a new Web Service with MARQUEZ_HOST, MARQUEZ_PORT and WEB_PORT configured privately. Gateway must be intentionally switched from existing Marquez Web to the new service after approved tests. Publishing the image does NOT deploy it and does NOT touch the original LAN NodePort.

Upstream: https://github.com/MarquezProject/marquez/tree/0.51.1/web
