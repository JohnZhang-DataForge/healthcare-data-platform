# Healthcare Data Platform — AI Agent entry

Applies to all work in this repository, regardless of AI assistant/tool. **Read before proposing, editing, testing, deploying or documenting changes.**

1. Read [documents/README.md](documents/README.md) and [AI/Agent rules](documents/engineering/development/AGENT-RULES.md).
2. For documentation work read [documentation governance](documents/engineering/development/DOCUMENTATION-GOVERNANCE.md) and [migration status](documents/engineering/migration/MIGRATION-STATUS.md).
3. Read [current project status](documents/engineering/status/PROJECT-STATUS.md) for the single cross-project CURRENT/NEXT, then only relevant current source, tests, contracts and verified evidence. The former `docs/` directory is **not in current Main**; historical documentation/evidence is preserved in the pre-removal Git snapshot `49936b51d4beadc69383e931efc3e72d2f0db47e`. Current `documents/` overrides old dated CURRENT/NEXT statements. For an unmigrated domain, use verified code and archived records as historical technical references. For an unmigrated domain preserve its still-effective contracts and safety constraints until a reviewed replacement exists.
4. Do not follow stale `CURRENT/NEXT` statements in dated handoffs over newer proven implementation/acceptance. Distinguish **planned / coded / tested / deployed / live verified**.
5. Use bounded, reviewable changes: latest `main` → branch → appropriate validation → PR. Never treat unmerged work as mainline completion.
6. Never execute Terraform `apply/destroy`, PostgreSQL business writes, destructive Kubernetes/S3 actions, or live shared-runtime operations solely because a document describes them. Require authorization and the existing safety gates. Do not disclose secrets.
7. Prefer existing Self-Runner workflows; bind evidence to the exact target commit SHA, run ID and data batch as applicable.
8. **Mandatory for all NEW maintained code**: name Python modules, DAGs, SQL, scripts, images, manifests, workflows and tests by **component/function**, NEVER by `taskNNN` / `stepNNN`. Read [Code Organization & Naming](documents/engineering/development/CODE-ORGANIZATION-AND-NAMING.md). Legacy runtime names remain until a separately tested, reviewed migration. When adding, deleting, or moving component source files, update the owning `documents/systems/data-platform/<component>/CODE.md` in the same PR (Airflow sample: [CODE.md](documents/systems/data-platform/airflow/CODE.md)); review CODE.md after material entry-point or dependency changes.
9. **Before any shared-runtime operation**, read [Safe Operations](documents/engineering/operations/SAFE-OPERATIONS.md) and [Session Coordination](documents/engineering/development/SESSION-COORDINATION.md). Never assume another Session's absence means its Spark/PG/K8s job is idle; unknown/conflicting operation = HOLD. Current progress belongs in PR/Run (and future OpenSpec Changes), not an ever-growing Handoff Markdown.
10. Documentation governance is active. The retired `docs/` is accessible only through Git history. OpenSpec G1 initialized the minimal `openspec/` structure; G2 project context, G3 validation CI and G4 agent/runner integration remain pending. Do not bulk-import historical docs or treat CLI initialization as business/runtime acceptance.

## Task-aware reading — do not load every guide by default

The current model is **source-first, workflow-driven**: maintain canonical application code, configuration and tests directly in Git; use reviewed Workflows for checks, packaging and authorized execution. Shell is a supporting tool, not the default way to generate application source. Read the baseline in rules 1 and 3, then only the relevant detailed guides. Combine rows for mixed tasks; shared-runtime work always requires rule 9.

| Task type | Additional reading before the relevant work |
| --- | --- |
| Code, tooling, Shell maintenance or refactor | [Development Workflow](documents/engineering/development/DEVELOPMENT-WORKFLOW.md), [Component-first Naming](documents/engineering/development/CODE-ORGANIZATION-AND-NAMING.md) and the owning component's `CODE.md`; inspect actual source and contracts |
| Unit, contract, replay, reconciliation or acceptance test | [Testing & Evidence](documents/engineering/development/TESTING-AND-EVIDENCE.md) and affected contracts; if the test touches a shared environment, also apply the runtime row |
| Shared K8s/Airflow/Spark/PostgreSQL/S3/Azure operation, deployment, Terraform plan, retry, reset, publish or recovery | [Safe Operations](documents/engineering/operations/SAFE-OPERATIONS.md) and [Session Coordination](documents/engineering/development/SESSION-COORDINATION.md); inspect the actual command/Workflow and get required authorization |
| Documentation change, navigation repair or docs migration | [Documentation Governance](documents/engineering/development/DOCUMENTATION-GOVERNANCE.md) and [Migration Status](documents/engineering/migration/MIGRATION-STATUS.md); review affected links and authority boundaries |
| Architecture or component behavior design | [System Overview](documents/architecture/SYSTEM-OVERVIEW.md), relevant component `README.md`/`CODE.md` and contracts; use OpenSpec only if separately requested and initialized |

Retired Skill and task-specific troubleshooting notes are historical references, not another active instruction set. Do not restore old generator-first workflows, hardcoded host paths or dated NEXT items as current rules.

These instructions supplement user instructions and current contracts; they do not confer runtime permissions. See the linked detailed rules for precedence and workflow.
