# Fabric Task 3.3 — offline integration acceptance and future live authorization boundary

> **Status: STATIC CONTRACT ONLY / HOLD.** This note is a gate checklist, not live resource inventory, proof of a reviewed binary Terraform plan, Azure/Fabric authorization, or payment approval. No new Capacity creation is authorized.

## Source and controller boundary

Self-Runner `fabric-controlled-entry.yml` (added by PR #150, committed to its protected Main) uses GitHub-hosted manual `workflow_dispatch` without cloud credentials, `dw-runner-set` jobs or Terraform commands. Its Python entry `src/ci/fabric_controlled_entry.py` returns a **JSON HOLD summary**, which **must be treated as user-supplied data** unless trusted provenance, actual immutable controller SHA and approved Healthcare SHA are checked independently. Passing an SHA as a CLI argument is *not* checking GitHub Main history. A typed Plan digest is *not* verification of a stored signed Plan.

The Healthcare-side tool `tools/fabric_execution_readiness.py` accepts the five **non-secret, value-only local JSON objects** below and an expected Healthcare SHA **claim**:

```bash
python3 azure-fabric/infra-terraform/tools/fabric_execution_readiness.py \
  --profile /path/to/profile.json \
  --resolved-clients /path/to/resolved-client-ids.json \
  --storage-target /path/to/storage-target-value.json \
  --capacity-target /path/to/capacity-target-value.json \
  --controller-intake /path/to/unverified-controller-intake.json \
  --expected-healthcare-sha <40-character-lowercase-commit>
```

Its `FABRIC_OFFLINE_INTEGRATION_HOLD` means the inputs are **internally consistent only**: exact isolated `fabric/<environment>/*.tfstate` targets, distinct Tenant A Backend and Tenant B Fabric identities, root/phase allowlisting, no forgery of offline approval flags, and allowed Capacity/Storage modes. No source SHA verification, Plan artifact or Terraform execution occurs. Unknown fields and secrets are rejected and never echoed. Tests use synthetic values only.

## Source-only acceptance matrix

| Mode | New Root / Phase | Static contract | Still-blocking proof |
| --- | --- | --- | --- |
| `reuse-existing` / existing Capacity | Bootstrap Identity/Storage/Capacity | Controller only HOLD | Seed rights, managed App names, initial local State custody, remote inventory |
| `reuse-existing` / existing Capacity | Plan Workspace/Onelake/Connection | Static handoff + isolated State keys HOLD | Real `johnzhang`/Capacity ownership, State vacancy, Provider/OIDC permissions, reader credentials |
| `fresh-bootstrap` / existing Capacity | Plan any new Root | Strict Profile-bound v2 HDP Storage Backend and Connection origin HOLD | Private Endpoints/DNS, protected State, independently checked new account, RBAC and Fabric connectivity |
| Either / new Capacity | Any phase | `STATIC_HANDOFF_HOLD_PAID_CAPACITY_UUID` | Independent actual SKU/price/consent, cloud resource readback, verified Fabric Capacity UUID (ARM ID is not equivalent) |
| All | Apply | Syntax-only requested Plan digest HOLD | Trusted immutable reviewed Plan artifact, hash+State snapshot+Source SHA binding, real human second approval, no destructive changes |

## Preconditions requiring separate explicit authorization for live execution

- Approved and recorded immutable Healthcare Main SHA + Self-Runner Main SHA (read independently from GitHub, with branch protection); dynamic PR refs or `main` argument not sufficient.
- Protected GitHub Environments for **independent** Seed/bootstrap, Plan and Apply scopes, actual reviewers and trusted OIDC issuer/audience/exact subject for the Backend Operator Tenant A and Fabric Deployer Tenant B.
- Real State inventory of *new* `fabric/<env>/{workspace,onelake,connection}.tfstate` and old `dev/*` (read-only; no import/migration), plus explicit ownership and disaster-recovery process for bootstrap local State.
- Real target Capacity Fabric UUID, Tenant/Sub ownership, tenant setting and permission inventory; Capacity `create-new` separately requires cost estimation, SKU quota, approved billing terms and trusted payment approval **before even considering actual Terraform execution**.
- Protected Storage network and Reader access including private endpoint, DNS and Fabric cross-tenant connection type compatibility; confirm existing Key Vault secret reference availability **without exposing its value**.
- Separate user approvals for a specific cloud `init/plan` and then the exact reviewed **saved** `apply` artifact; independently enforce no deletion/replacement, wrong State, or wrong account. Static flags are claims and do not establish real access.
- Actual provider install/Schema validation and access are deliberately excluded from CI. `terraform fmt -check` is not `terraform validate`.

## Evidence and next actions

The GitHub-hosted `Fabric Environment Preflight (Offline)` PR workflow covers all six Terraform Roots' **format-only** validation, Python negative contracts, static ownership and the new integrated HOLD report. Preserve a PR HEAD, six relevant check names/conclusions, GitHub-hosted workflow run ID, merged Main SHA and exact root files in the OpenSpec task log; record **no real deployment**. After code-only acceptance, Task 3.3 may mark the *offline verification* slice as complete, but Task 3.4 Closeout/Archive must remain HOLD until independently authorized live proof exists.

## Verified PR CI record (source-only; not runtime attestation)

- PR #298 (source-only integration): <https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/298>
- Reviewed exact Git source HEAD: `bfcd37d966654a16eb5ed63ef404496175c96c88`
- Fabric Environment Preflight (Offline) GitHub-hosted run: <https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39403368850> — `success`, includes `test_fabric_execution_readiness.py` and all existing Root policy suites and `terraform fmt -check -diff` across six Root directories.
- Other checked gates at same HEAD: Documentation Relative Links, Component Code Naming, OpenSpec Static Validation, OpenSpec Change Gate, OpenSpec Trusted Change Gate — all success.
- Post-merge Healthcare Main at acceptance: `8388410313c863eaf9e4b199fb476d4ff8c00586`.
- Self-Runner separate offline controller baseline: `a951cb5e8589815cc1adb2096252e2c221dd0184`; PR #150 GitHub-hosted safety policy run `39394922136` success.
- GitHub PR #298 changed **only six** in-scope offline files; older Azure/Fabric resources, legacy seven Roots, Self-Runner `azure-infra.yaml` and State untouched. **Task 2.5 and Task 3.3 offline acceptance concluded; live deployment remains HOLD.**

Acceptance record is **read-only historical CI evidence**, not a directive for a workflow_dispatch; Task 3.2's privileged execution design and Task 3.4's live acceptance remain independently blocked.
