# Marquito upstream feasibility and reuse gate

Status: **RESEARCH COMPLETE / REDISTRIBUTION HOLD / LOCAL BUILD NOT RUN** (2026-10-27). This is a read-only review of the author's public GitHub source, not a fork, build artifact, or publishing authorization.

## Upstream sources inspected

- Repository: [spark-sandbox/projects/marquito](https://github.com/mdrakiburrahman/spark-sandbox/tree/main/projects/marquito); reviewed code-search revision `2683e5f81843270093006a3d0c8b60dcc348345a`, with individual file contents read from upstream `main`.
- [package.json](https://github.com/mdrakiburrahman/spark-sandbox/blob/main/projects/marquito/package.json): Next.js 15.1.0, React 18, Fluent UI 9, XYFlow 12, Dagre, Jest 29. `npm run build` invokes `next build`; `npm run test` invokes Jest.
- [next.config.mjs](https://github.com/mdrakiburrahman/spark-sandbox/blob/main/projects/marquito/next.config.mjs): `output: 'export'`, `trailingSlash: true`, unoptimized images. The resulting static `out/` tree is suitable *in principle* for static hosting, but an actual clean `npm ci && npm run build` and anonymous-browser acceptance still need evidence. Build ignores ESLint errors.
- [src/lib/parseLineage.ts](https://github.com/mdrakiburrahman/spark-sandbox/blob/main/projects/marquito/src/lib/parseLineage.ts): consumes newline-delimited **OpenLineage RunEvent objects**, with `eventType`, `eventTime`, `job.namespace/name`, `run.runId`, `inputs[]`, `outputs[]`. Reads `output.facets.schema.fields` and `output.facets.columnLineage.fields[targetColumn].inputFields[]`; returns Jobs, Dataset, Table and Column edge data. A summary snapshot is **not** suitable input for this parser.
- [src/components/DataSourcePicker.tsx](https://github.com/mdrakiburrahman/spark-sandbox/blob/main/projects/marquito/src/components/DataSourcePicker.tsx): currently chooses author sample data or uploads a local JSONL file; no Healthcare automatic static endpoint selection.
- [src/app/page.tsx](https://github.com/mdrakiburrahman/spark-sandbox/blob/main/projects/marquito/src/app/page.tsx): client state calls `DataSourcePicker`, then renders `HeroSection`, `TableLineage`, `ColumnLineage`, `JobsTable`, `DatasetsTable`, and `EventsTimeline`.
- [TableLineage](https://github.com/mdrakiburrahman/spark-sandbox/blob/main/projects/marquito/src/components/TableLineage.tsx) / [ColumnLineage](https://github.com/mdrakiburrahman/spark-sandbox/blob/main/projects/marquito/src/components/ColumnLineage.tsx): XYFlow/Dagre nodes and interactive column trace already exist; **reuse these rather than making a second graph engine**.
- [upstream parser tests](https://github.com/mdrakiburrahman/spark-sandbox/blob/main/projects/marquito/__tests__/parseLineage.test.ts) include START/COMPLETE, schema and column facets.

## Compatibility and security findings

1. `GET /data/latest.json` is the **frozen** `portal.snapshot.v1` summary (origin, last successful timestamp, optional verification evidence). It **cannot** be passed to the upstream OpenLineage parser. `GET /data/lineage/latest.jsonl` is an **additional candidate** for A/B; **Coordinator approval remains mandatory**. No alteration of the P0 JSON Schema, fixtures, or published URL contract is authorized here.
2. Upstream `fetchLineageData(localPath)` can read a same-origin static JSONL file without a server or Marquez API, once this path is approved and author reuse is licensed. Integration should supply the static route and use the existing `parseLineageText`; do not copy that implementation into our repo before license clearance.
3. Upstream parser requires actual arrays even for events with no input/output; a missing `inputs` or `outputs` crashes parsing. Job map and table edge IDs use **job name alone**, not `namespace + name`; names colliding across namespaces could merge graph nodes, so B must emit non-colliding public job names or integration needs a reviewed, licensed patch. The parser may deduplicate table edges across multiple runs; it is a visualization, not immutable run-level provenance.
4. Table links come from actual event input/output; column links come from output columnLineage facets. No inferred links based on dataset name, hospital city, or Azure/Local similarity. The site must distinguish summarized proof from JSONL that has **not yet been evidence-linked** to that snapshot.
5. Upstream samples/download URLs refer to the author's Azure Blob endpoint and should be hidden/replaced **after authorization**; otherwise the public site would mix external samples with our Healthcare provenance. Do not inject private URI, SQL, IP, tokens, PHI, or unreviewed raw Marquez facets into publicly served JSONL.
6. Static GET/refresh must not invoke `/api/demo/trigger` or other dispatch endpoints. Failure to read a newer resource must never replace a previously published success with a falsely labeled LIVE result. Empty JSONL means no graph, not a successful execution.
7. No LICENSE was found at the inspected repository root or within `projects/marquito/`; absence of a file is **not** permission for redistribution or public deployment. Obtain explicit rights from the author or a verifiable license that covers the intended use and attribution before importing frontend/parser/graph code. Dependency licenses must also be reviewed.

## Intended adapter boundary (independently written)

Own source directory: `platform-portal/portal/web/`. Implement a tiny read-only loader that reads the frozen P0 summary first, then optionally the candidate same-origin JSONL; validates minimal event shape before handing **unaltered JSONL text** to the upstream parser. Display `MOCK` with `mock_notice`, or `VERIFIED_EXPORT` only when the P0 evidence gate is satisfied. Even then, **do not claim JSONL verified by association** before B establishes publication-time pairing and manifest checks.

A later licensed integration should replace *only the upstream data-selection wiring/status banner*, keeping the author's page/graph/parser implementation. Until then, implement and test an independently authored adapter only. Do not publish the author's protected code, or run a Cloudflare deployment.

## Gates to finish

- **HOLD**: author's written redistribution/modification/static-deployment permission, or demonstrably applicable license.
- **HOLD**: A/B and Coordinator formally accept the candidate JSONL URL and define snapshot/JSONL pairing/last-success publish semantics.
- **NOT RUN**: `npm ci && npm test && npm run build` on a legally reusable upstream tree; `out/index.html`, Table and Column Lineage browser acceptance using sanitized events.
- **NOT RUN**: any real historical Marquez events (Agent B), Cloudflare deployment, runtime write, Fabric, or Azure operation.

Source-only research was performed with GitHub read operations. **Runtime side effects: none.**
