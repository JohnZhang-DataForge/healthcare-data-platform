# Proposal — Restore canonical-first shared processing architecture in current documentation

## Why

The approved 2026-10-30 Medallion Canonical ADR and 2026-10-31 Fabric-native ADR define source-specific CSV/FHIR/HL7 adapters, a single Canonical Patient/Encounter contract, shared post-Canonical OMOP business logic, and platform-owned physical publishers. However active architecture entry points `documents/architecture/SYSTEM-OVERVIEW.md`, `DATA-FLOW.md` and `decisions/README.md` still promote the 2026-10-16 PG-export-only Fabric plan, including stale "no Workspace/Notebook/Lakehouse/Warehouse" claims. New agents following those links may implement a second engine or mistake the PG snapshot product for the active FHIR intake.

## What Changes

- Restore two explicitly distinct Azure/Fabric paths: active synthetic FHIR R4 through Bronze/Approved Canonical Silver/OMOP Candidate/Warehouse Gold, and separately proposed Local PostgreSQL OMOP snapshot to cloud analytics.
- Establish authoritative architecture routing from the documentation index and system overviews to the 2026-10-30/31 ADRs and Shared Engine ownership; retain source-system-specific mapping profiles and platform-specific physical writers.
- Record actual single-wheel 0.1.3 implementation and observed G4 Silver/F0-F2 evidence without upgrading Candidate/Gold/Pipeline from OPEN.
- Distinguish reuse of **contracts and algorithms** (agreed target) from reuse of the **same package by both local and Fabric runtimes** (migration not yet complete).
- Preserve historical fixed-SHA run references and older decisions as history, not current operational instructions.

## Scope / Non-goals

Docs/OpenSpec only. No Python, SQL, GitHub workflow, OIDC, Cloudflare, Terraform, Fabric/OneLake/Blob/PG/S3/K8s read-write operations or runtime calls. No schema change, no migration of Local DP runtime, no rewrite of approved ADRs, and no claim of Gold E2E success. The existing business OpenSpec changes remain responsible for G5 P1–P5 acceptance.
