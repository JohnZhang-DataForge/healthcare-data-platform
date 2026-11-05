# Tasks — Fabric deployment owner layout and bounded Warehouse/OpenLineage migration

## P0 — Inspect and approve architecture
- [x] 0.1 Verify latest Healthcare main `9fbed5a4d4995af53b2f7ab08426f9b1312192e1`, no open Healthcare PRs; inspect the 51 Warehouse and 2 OpenLineage source files, adopted repository-layout spec, existing Fabric CI and CODE maps.
- [x] 0.2 Inspect private Self-Runner current main `2fcbbb16344d845d124e66804eea4a2bbae8dc6d`: its active Schema/Identity/Vocabulary deploy Python consumers reference old Warehouse paths; some historical workflows use frozen old Healthcare SHA. Record migration ordering and HOLD requirements.
- [x] 0.3 PR #698 merged to main `997b48d775a48844cdcd9a337d0490bd4eacc6d4` after Required `require-trusted-change` and `validate-openspec` SUCCESS; planning is not source migration.

## P1 — Enforce stable owner contract
- [x] 1.1 Publish one tracked registry defining all seven deployment components and code/source/test/doc ownership; do not create fake empty Git directories or a second Wheel.
- [x] 1.2 Extend applicable architecture docs, CODE map, Agent entrypoints and compatible non-protected layout checks; test positive and negative path cases.
- [x] 1.3 **ENFORCED — GitHub Ruleset #25365902 active with three Required GitHub Actions checks (`require-trusted-change`, `validate-openspec`, `require-trusted-fabric-deployment-owner`), all integration 15368 and no bypass actors.** PR #704 was temporarily made non-Draft; trusted owner job #127576406323 failed on the deliberate `deployment/rogue/` path while both original Required checks passed; GitHub reported `mergeable_state=blocked`; PR #704 was closed unmerged. Positive PR #703 passed. Existing protected checker and 185-path baseline preserved.

## P2 — Self-Runner compatibility first
- [x] 2.1 Inventory current-main and historical SHA-pinned Schema/Vocabulary consumers; historical workflows checkout fixed Healthcare SHA and keep historical paths.
- [x] 2.2 Add safe old/new-path read compatibility to current-main consumers with offline tests and independent SHA-pinned workflow safeguards.
- [x] 2.3 Self-Runner PR #524 merged main `e70f08afeb96a2665341ea4c687977662ca9c34b`; offline tests PASS, deployment jobs skipped, no Fabric SQL or cloud writes.

## P3 — Physical Warehouse/OpenLineage migration
- [x] 3.1 Move 49 reviewed SQL/metadata/Listener Git blobs byte-identically into deployment owners; Warehouse Writer and OpenLineage Publisher remain in component-source owners. Physical PR acceptance pending.
- [x] 3.2 PR #700 migrated all reviewed Healthcare offline imports, three CI trigger configurations, CODE owners, active/current contracts and relative links; check-links SUCCESS on final PR HEAD.
- [x] 3.3 Final PR #700 checks: CDM 2/2, Foundation 31/31, OpenLineage 8/8, quality Owner, documentation links, OpenSpec, repository layout and CODE-map trusted checks PASS. Independent base/head Git-tree comparison: 49/49 identical Git blob SHAs and old paths all absent, 11/11 Native blobs and 4/4 Writer/Publisher blobs unchanged; no live deployment calls.
- [x] 3.4 PR #700 merged main `8250b9b37cd4db3290569d2b4ea38f5296b38a88` with `require-trusted-change` and `validate-openspec` SUCCESS; Self-Runner #524 already merged and verified. External Cloudflare healthcare-portal build FAILED on migration PR but is not a Ruleset Required Check nor Fabric/SQL acceptance.

## P4 — Independent acceptance and adoption
- [x] 4.1 Independent post-merge main Git-tree readback at `8250b9b37cd4db3290569d2b4ea38f5296b38a88`: `deployment/warehouse/omop-cdm-5.4/` 41 assets, `deployment/warehouse/omop-foundation/` 7 assets, `deployment/openlineage/compatibility.py` 1; no old SQL/config assets; 3 Writer Python, 1 Publisher Python, and 11 Native Item blobs retained. CI per exact final PR head `1f95d45e520aebb8f938142f1fa1b46192102d1e`: [PR #700 checks](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/700/checks).
- [x] 4.2 With Required trusted enforcement and real non-Draft negative merge blocking verified, adopt `openspec/specs/fabric-deployment-component-ownership/spec.md` and archive this Change under `openspec/changes/archive/2026-11-05-standardize-fabric-deployment-component-layout/` through a protected PR. No Warehouse Gold, Spark Listener runtime or Fabric cloud deployment acceptance is claimed; independent final PR merge/main readback is required.

## Post-merge implementation evidence — 2026-11-05 ET

- Healthcare [#698](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/698) OpenSpec plan merged `997b48d775a48844cdcd9a337d0490bd4eacc6d4`; [#699](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/699) seven-owner registry and offline checker merged `90d57277047b44849a676e936672cf9fab2cefd6`.
- Private Self-Runner [#524](https://github.com/JohnZhang-DataForge/Self-Runner/pull/524) old/new exact schema source compatibility merged `e70f08afeb96a2665341ea4c687977662ca9c34b`; all offline checks PASS, real deploy jobs were skipped and original fixed historical Healthcare SHAs preserved.
- Healthcare [#700](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/700) 49 unchanged blob moves and dependent test/workflow/CODE references merged `8250b9b37cd4db3290569d2b4ea38f5296b38a88`. Offline CDM 2, Foundation 31 and OpenLineage 8 ran and passed; the required trusted check confirmed `REPOSITORY_LAYOUT_GATE=PASS` and `CODE_MAP_GATE=PASS` and all documentation links passed. No Azure/Fabric/SQL/Marquez runtime used for migration.
- Remaining is narrowly scoped **trusted Required enforcement of the newly introduced deployment ownership registry** (task 1.3, and thus archive 4.2). Do not present the optional head-branch ownership workflow alone as unbypassable. Existing source and test locations are already stable and can be used for ongoing development under the current enforced checks.

## P1.3 trusted workflow security

The new job always runs on pull requests without path filters. It checks out main policy and test code separately, treating the candidate checkout only as passive Git file data, and rejects ordinary PR modifications to its registry/checker/test/workflow after bootstrap. It has `contents: read`, no secrets and no deployment actions. **Do not mark P1.3 complete until exact GitHub Ruleset readback and negative PR blocked evidence.**

## P1.3 genuine PR check trials

- Trusted workflow introduced by [PR #702](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/702), merged main `2abba5b3f51056235c7967f9e2ef3a131c943d70`. This was the expected-allow path: PR #703 head `c7198e81962d979dc36df17a6cb8fae412617734` returned `require-trusted-fabric-deployment-owner=SUCCESS` (GitHub job 127570806130), as did existing `require-trusted-change`, `validate-openspec`, Change Gate and links; #703 merged `c782b5c861e8e2b3a24c82825bde18b01b20a893`.

## Independent negative PR proof and remaining administrator-only step

- [Deliberate negative Draft PR #704](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/704), exact PR HEAD `f98ebd2bbd2a25a30cc71941e0aecfa635e7bdd3`: the legitimate OpenSpec Task/Code Map bindings passed their own checks, while trusted owner job `127571470512` ran nine policy regressions, emitted `FABRIC_DEPLOYMENT_OWNER_VIOLATION=azure-fabric/deployment/rogue/probe.py:unregistered-deployment-component` and terminated with `FABRIC_DEPLOYMENT_OWNER_TRUSTED=FAIL`. Its untrusted optional owner check also failed. Draft is NEVER MERGE; no runtime side effects.
- GitHub Ruleset `25365902` independently queried after this negative run: only `require-trusted-change` and `validate-openspec` (both integration ID `15368`) are Required. The new trusted owner job is **NOT Required** and therefore PR #704's failed check alone does **not** prove GitHub merge blocking.
- **Admin action still required:** Settings → Rules → Rulesets → `main-openspec-ci-protection` → Required status checks → add `require-trusted-fabric-deployment-owner` from GitHub Actions, retain the two existing checks and empty bypass actors; save. Independently GET Ruleset and inspect exact new context/integration, then mark test PR Ready only long enough to verify `mergeable_state=blocked` due to the new Required failure; re-draft or close unmerged. Do not archive the OpenSpec until these proofs pass.

## 最终 P1.3 / P4.2 接受证明 — 2026-11-05 ET

- **User admin action independently confirmed:** [main Ruleset #25365902](https://github.com/JohnZhang-DataForge/healthcare-data-platform/rules/25365902) is `active`; Required contexts are `require-trusted-change`, `validate-openspec`, and `require-trusted-fabric-deployment-owner`, each with GitHub Actions integration ID `15368`, bypass actors `[]`.
- **Positive PR:** [#703](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/703) trusted deployment-owner job `127570806130` SUCCESS, original Required checks SUCCESS; squash merge `c782b5c861e8e2b3a24c82825bde18b01b20a893`.
- **Negative PR:** [#704](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/704) at `5607d562bbdc0b9defe8415158eafab9458ec69c` was **non-Draft** during the independent GitHub Ruleset mergeability inspection. The latest trusted owner job `127576406323` ran nine policy tests and then emitted `FABRIC_DEPLOYMENT_OWNER_VIOLATION=azure-fabric/deployment/rogue/probe.py:unregistered-deployment-component`, `FABRIC_DEPLOYMENT_OWNER_TRUSTED=FAIL`. Original Required `require-trusted-change` job `127576407100` and `validate-openspec` were SUCCESS; GitHub returned `mergeable_state=blocked`, `merged=false`. The deliberate negative PR was then **closed unmerged**. The illegal path never entered `main`.
- The trusted workflow is `.github/workflows/fabric-deployment-ownership-trusted.yml` (`pull_request_target`); its policy/registry/tests load from trusted default-branch `main`, and PR HEAD is read solely as passive Git/tree/text. No Azure, SQL, Blob, Fabric API, K8s or Marquez operations were initiated by this governance acceptance.
- This accepted source/governance change does not imply G5/OMOP Gold COMMIT or runtime OpenLineage Listener verification. Those remain governed by their own independent business Changes.
- **Archive PR condition:** The archival relocation itself must pass all three Required checks and applicable docs/OpenSpec tests, be merged normally to protected `main`, and be independently read back. Its Git History preserves the original active proposal/design/spec/acceptance.
