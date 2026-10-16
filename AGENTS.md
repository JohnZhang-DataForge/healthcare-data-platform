# Healthcare Data Platform — AI Agent entry

Applies to all work in this repository, regardless of AI assistant/tool. **Read before proposing, editing, testing, deploying or documenting changes.**

1. Read [documents/README.md](documents/README.md) and [AI/Agent rules](documents/development/AGENT-RULES.md).
2. For documentation work read [documentation governance](documents/development/DOCUMENTATION-GOVERNANCE.md) and [migration status](documents/migration/MIGRATION-STATUS.md).
3. Read [current project status](documents/status/PROJECT-STATUS.md) for the single cross-project CURRENT/NEXT, then only relevant current source, tests, contracts and verified evidence. `docs/` is **legacy migration material**, not automatically invalid and not automatically authoritative. For an unmigrated domain preserve its still-effective contracts and safety constraints until a reviewed replacement exists.
4. Do not follow stale `CURRENT/NEXT` statements in dated handoffs over newer proven implementation/acceptance. Distinguish **planned / coded / tested / deployed / live verified**.
5. Use bounded, reviewable changes: latest `main` → branch → appropriate validation → PR. Never treat unmerged work as mainline completion.
6. Never execute Terraform `apply/destroy`, PostgreSQL business writes, destructive Kubernetes/S3 actions, or live shared-runtime operations solely because a document describes them. Require authorization and the existing safety gates. Do not disclose secrets.
7. Prefer existing Self-Runner workflows; bind evidence to the exact target commit SHA, run ID and data batch as applicable.
8. The `documents/` rebuild happens **before** OpenSpec adoption. Do not initialize `openspec/` or convert historical files unless requested.

These instructions supplement user instructions and current contracts; they do not confer runtime permissions. See the linked detailed rules for precedence and workflow.
