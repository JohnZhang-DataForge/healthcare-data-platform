# P5 Independent Governance QA — 2026-11-04 ET

> **Scope:** Healthcare repository layout only; no Fabric/Azure/Local runtime tests or production writes. P5 tasks 5.1–5.3 are evidence-accepted. **P5.4 remains OPEN** while the intentionally immutable policy-baseline retirement decision is unresolved.

## Main / PR lineage

- Latest main independently inspected for this audit: `0f72dc7a1c943aac817046cbc6ce20c4815c6317`.
- P1: [#672](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/672), policy correction [#674](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/674), post-fix protected positive [#676](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/676) and deliberately blocked negative [#675](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/675).
- P2 documentation migration: merged [#677](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/677).
- P3 15 tests in three independently protected PRs: [#678](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/678) Notebook 8, [#679](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/679) OpenLineage 2, [#680](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/680) Warehouse 5. The latter merged safely on top of concurrent Marquez/Portal main changes after comparing disjoint Git-tree paths.
- P4 helper/ownership audit: merged [#687](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/687); both genuinely invoked auxiliary Python files remain in their original directories instead of a gratuitous relocation.

## Exact file and test inventory (independent Git trees / source reads)

- Original fixed pre-P1 SHA `ee435d8720cfed698e239f767f313addf36a924e`; compared against merged main `0f72dc7a1c943aac817046cbc6ce20c4815c6317`, untruncated Git trees.
- All **15/15** Fabric `test_*.py` files under `.github/quality/tests/azure-fabric/`, zero under the old `azure-fabric/**/tests/` paths.
- Independent per-file `def test_*` name comparisons for **all 15 pairs**, original vs current: **118/118 exact method names retained**. CI's *executed* results are **87 Notebook + 8 OpenLineage + 33 Warehouse = 128 tests**; this is larger than 118 definitions because unittest suite collection includes inherited cases.
- **8/8** source README and **2/2** other source explanatory Markdown retired from `azure-fabric/`; all unique technical contracts now have owners under `documents/systems/azure-fabric/`, with reverse links repaired.
- **11/11** Fabric native item Git blobs exactly byte-identical to pre-P1 baseline; **209/209** non-test/non-Markdown Fabric source blobs unchanged. No new Git-native Warehouse Item was fabricated.
- Source-side quality contracts remain owned by original components: `azure-fabric/warehouse/` SQL/Writer, `azure-fabric/openlineage/` business compatibility/Publisher, native `azure-fabric/workspaces/healthcare-omop/`. No duplicated business source or second Wheel.
- The audited Self-Runner main (then `10ef1321fd7a191c2a418700e331551ba523ce2e`) had four legacy test path references in tracked Workflow files, each checked out an **immutable historical Healthcare SHA** containing those paths. No latest-main unpinned workflow dependency on retired paths found in the audited Workflow set. We did not edit those original historical source pins.

## Actual quality and protection evidence

- Notebook [P3.1 Run #41956396029](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41956396029) job `127012200184`: 8 files, `FABRIC_NOTEBOOK_DISCOVERED=87; required_min=87`, `Ran 87 tests`, PASS, expected Native runtime HALT.
- OpenLineage [P3.2 Run #41956789788](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41956789788): 2 files, `Ran 8 tests`, no cloud writes.
- Warehouse [P3.3 CI #680](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/680/checks): exact 1 CDM file / 2 executed tests; 4 Identity Foundation files / 31 executed tests. Both PASS on final rebased head alongside Required checks.
- Active GitHub Ruleset `25365902` retains `require-trusted-change` and `validate-openspec`, GitHub Actions integration `15368`, with no bypass; positive [#680](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/680) and [#687](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/687) merged with both protected checks SUCCESS.
- **New P5 negative:** [#689](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/689), closed unmerged. It intentionally reintroduced two *formerly exact-allowlisted but now deleted* paths: old Notebook `README.md` and old `tests/test_notebook_offline.py`. The actual [Required run #41964641595](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41964641595) job `127038703947` failed with `RULE=new-source-document EXPECTED_OWNER=documents/` and `RULE=new-test-outside-quality EXPECTED_OWNER=.github/quality/tests/`. GitHub `mergeable_state=blocked`. Neither invalid file entered main.
- P4 independent review and normal protected merge verified; other agents' Marquez/Portal PRs were not modified by these Fabric moves.
- The unrelated external Cloudflare `Workers Builds: healthcare-portal` check sometimes FAILED on Fabric-only docs/test PRs. It is not a Ruleset Required Check and remains a separately owned investigation; no portal changes were made to silence it.

## Immutable P1 baseline / P5.4 outstanding governance decision

- Current file `.github/quality/repository-layout-legacy-baseline.txt` is an **immutable P1 historical inventory** containing 185 exact originally approved exceptions.
- Only **160/185** entries correspond to still-present paths in the audited main; the remaining **25/185** are **all the retired Fabric test/doc paths**, and no other baseline entry is missing.
- Crucially, the trusted checker requires **both** `path in baseline` **and** `path in PR base tree` for a legacy path to remain eligible. Therefore the 25 retired entries are **not an active reintroduction privilege**. The real negative #689 proves this under enforced branch rules.
- The approved Design originally proposed **removing those 25 entries from the literal frozen policy file** during P5. That file itself is in trusted `GUARD_FILES`: a normal PR editing it yields `trusted-policy-mutation` and cannot pass `require-trusted-change`. We **have not modified the protected policy** or bypassed any Ruleset.
- **Decision still needed for 5.4:** either preserve this auditable frozen 185-row historical snapshot as-is (effective active exceptions are 160, with real negative proof) through an explicitly approved OpenSpec design adjustment; **or** perform a separately approved one-time GitHub Ruleset maintenance window to prune 25 rows (never silently bypass checks). Until one of those is approved/closed, **P5.4 and archive remain OPEN**, even though no functional loophole was found.

## Source safety and future follow-up

- Our P1–P5 Git work had no Azure/Fabric Spark execution, Warehouse DDL/DML, GHCR publish, local K8s/Marquez modification or data replay; CI runs cited above are offline/static. Other independent Marquez/Portal agents may perform separate runtime work, which this audit does not assess.
- The detailed placement and fixture policy is in [Testing & Evidence](../../../../documents/engineering/development/TESTING-AND-EVIDENCE.md). Dedicated Fabric CI groups now enforce actual nonzero test discovery/counts. This does **not** yet establish a universal future auto-discovery gate for every possible new Local/Portal/Shared test component; treat that as a separate governance improvement, not as current P5 proof.
