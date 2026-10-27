# Public Portal Web — first-party static data adapter

**Scope: 7.2 partial implementation. NOT A DEPLOYABLE MARQUITO SITE.**

This directory contains only original Healthcare code, an intentionally fictional OpenLineage sample, and Node.js offline tests. The author's protected Next.js pages, parser and XYFlow/Dagre graphs are **not** vendored here. Reuse and Cloudflare publication are **HOLD** until legal rights and A/B static data acceptance are confirmed.

## How the pieces fit

- `src/publicDataSource.mjs` is a browser-compatible, dependency-free, GET-only reader for frozen P0 `/data/latest.json` and **candidate** `/data/lineage/latest.jsonl`. It does not alter `portal.snapshot.v1`.
- The static lineage route is **not yet approved**. The Coordinator must align it with Agent B and the verified-snapshot publish protocol. Do not publish a sample file at that public path just because it exists in `test/fixtures`.
- `validatePublicJsonl` checks a restricted, public-facing projection of OpenLineage RunEvents before a later licensed integration can call Marquito's `parseLineageText(result.lineageText)`. It does not draw graphs, rewrite the author's parser, perform publication-time redaction, or independently prove JSONL belongs to the summary.
- The code rejects unapproved event/run/job/dataset facets instead of silently exposing arbitrary internal Spark/SQL properties. Agent B remains responsible for publication-time PHI/SQL/private-URI/credential scrub and independent verification. Upstream graph expects `inputs[]`/`outputs[]`, namespace/name, and output `schema`/`columnLineage` facets.
- When the snapshot is missing, show a failure state; when lineage is missing/invalid/empty, preserve the P0 last-successful **summary** and show a warning/no graph. During a single browser session, `previous` can preserve a previously validated successful graph on network errors; it is not stored to disk or advertised as a new success. A different `snapshot_id` cannot inherit the old graph.
- `dataOrigin=MOCK` must prominently display the P0 `mock_notice`. `VERIFIED_EXPORT` requires P0 source/manifest/GitHub Run evidence, but this adapter **still labels lineage JSONL `UNVERIFIED_CANDIDATE`** until Agent B establishes a separately evidenced linkage.
- No POST, authenticated API, Cloudflare Worker, database, Azure or private Marquez connection exists in this module.

## Tests

From this directory, with Node.js 22 or later:

```sh
node --test test/publicDataSource.test.mjs
```

The tests consume the actual P0 mock snapshot from `../fixtures/snapshot.mock.json` and an independently authored synthetic two-event JSONL. No PHI or real hospital claims.

## Future licensed Marquito wiring (not implemented)

1. Confirm rights to reuse, modify and publicly distribute the author's frontend; record attribution and applicable dependency licenses.
2. Integrate the reader into the **existing** upstream DataSourcePicker/Home flow. Pass validated `lineageText` to its parser and leave its original TableLineage/ColumnLineage graph components in place.
3. Remove/replace upstream sample Azure Blob links. Keep the page anonymous, read-only, and clearly label summary provenance separately from event provenance.
4. Prove `npm ci && npm test && npm run build`, inspect `out/`, and browser-test Table/Column edges against Agent B sanitized historical events plus empty/failure scenarios. Test the exact intended commit. This has **not** been done.
5. Only after Coordinator approval may Cloudflare be configured manually by the user.

For the upstream technical review see [UPSTREAM-REVIEW](UPSTREAM-REVIEW.md) on the separate 7.1 PR. Those two agent branches are intentionally independent; Main Session coordinates merges.
