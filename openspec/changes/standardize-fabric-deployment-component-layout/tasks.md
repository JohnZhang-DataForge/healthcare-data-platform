# Tasks — Fabric deployment owner layout and bounded Warehouse/OpenLineage migration

## P0 — Inspect and approve architecture
- [x] 0.1 Verify latest Healthcare main `9fbed5a4d4995af53b2f7ab08426f9b1312192e1`, no open Healthcare PRs; inspect the 51 Warehouse and 2 OpenLineage source files, adopted repository-layout spec, existing Fabric CI and CODE maps.
- [x] 0.2 Inspect private Self-Runner current main `2fcbbb16344d845d124e66804eea4a2bbae8dc6d`: its active Schema/Identity/Vocabulary deploy Python consumers reference old Warehouse paths; some historical workflows use frozen old Healthcare SHA. Record migration ordering and HOLD requirements.
- [x] 0.3 PR #698 merged to main `997b48d775a48844cdcd9a337d0490bd4eacc6d4` after Required `require-trusted-change` and `validate-openspec` SUCCESS; planning is not source migration.

## P1 — Enforce stable owner contract
- [x] 1.1 Publish one tracked registry defining all seven deployment components and code/source/test/doc ownership; do not create fake empty Git directories or a second Wheel.
- [x] 1.2 Extend applicable architecture docs, CODE map, Agent entrypoints and compatible non-protected layout checks; test positive and negative path cases.
- [ ] 1.3 Verify that the applicable PR check is actually Required; if trusted checker cannot be updated under repository protection, preserve a HOLD and use the approved governance path rather than weakening protections.

## P2 — Self-Runner compatibility first
- [ ] 2.1 Inventory all current-main and SHA-pinned Self-Runner Warehouse/OpenLineage consumer paths.
- [ ] 2.2 Add safe old/new-path read compatibility to current-main consumers with offline tests and independent SHA-pinned workflow safeguards.
- [ ] 2.3 Record a merged, successful Self-Runner compatibility PR; no real SQL or cloud operations.

## P3 — Physical Warehouse/OpenLineage migration
- [ ] 3.1 Move reviewed SQL/metadata and Listener candidate configuration to deployment owners, byte-identical; retain Warehouse Writer and OpenLineage Publisher in component-source owners.
- [ ] 3.2 Update all Healthcare imports/tests/CI paths, CODE owner maps and current docs/OpenSpec references in the same bounded PRs.
- [ ] 3.3 Run 2 CDM + 31 Foundation + 8 OpenLineage offline cases, static link and trusted layout checks; verify SHA/blobs, no native item or runtime mutation.
- [ ] 3.4 Merge only with Required Checks passing and all unpinned consumer paths compatible.

## P4 — Independent acceptance and adoption
- [ ] 4.1 Independent latest-main Git tree, CODE map and offline CI readback; link actual PR/Run/commit evidence.
- [ ] 4.2 Adopt a current layout spec and archive this change only after cross-repo path migration is accepted, reporting remaining runtime tasks separately.
