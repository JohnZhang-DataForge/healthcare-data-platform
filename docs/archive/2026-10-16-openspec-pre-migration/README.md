# OpenSpec migration — pre-migration documentation snapshot (2026-10-16)

> **BACKUP / HISTORICAL / READ-ONLY — NOT CURRENT INSTRUCTIONS**
>
> This directory is a complete, content-preserving snapshot of the `docs/` tree before adopting OpenSpec in the same repository. It is a **copy**; original files were not moved, edited, or deleted. Do **not** treat historical `CURRENT` / `NEXT` statements in this snapshot as current project state.

## Source of truth at backup time

- Repository: `JohnZhang-DataForge/healthcare-data-platform`
- Source ref: `main`
- Exact source commit SHA: `151f635db561fc01db04a2003ebfa8797a926cbd`
- Exact source root Git tree SHA: `5c184125e87d6a6d176470d6b4a4f291903062b3`
- Backup date: `2026-10-16` (America/New_York)
- Source directory: `docs/`
- Original Markdown files captured: **147**
- Total original Markdown bytes: **1194993**
- Files already under original `docs/archive/`: **36** (included to make this a full snapshot)
- Source at the exact commit: https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/151f635db561fc01db04a2003ebfa8797a926cbd/docs

## Contents

- `snapshot/`: copied Git blobs from **all files** under the source `docs/` directory, with their original relative subdirectory structure retained. For example `docs/README.md` becomes `snapshot/README.md`, and `docs/archive/X.md` becomes `snapshot/archive/X.md`.
- `MANIFEST.tsv`: full mapping of original repository paths, exact Git blob SHA and source byte sizes. Blob SHAs are preserved without re-encoding or rewriting the original Markdown.

## Verification / restoration

To verify, compare each `MANIFEST.tsv` Git blob SHA against the corresponding file under `snapshot/` in the backup commit. All **147** snapshot entries should have identical blob SHAs to the source commit. The source SHA above also permits recovering the unmodified original `docs/` tree directly from Git history.

This snapshot is frozen as the **pre-OpenSpec migration baseline**. Subsequent OpenSpec changes, documentation refactoring and archival actions should occur **outside** this snapshot. The current `docs/` and future `openspec/` directories remain the locations for live documentation and behavior specifications.

**Scope:** documentation backup only. No business source, Terraform, workflow, Kubernetes, PostgreSQL, runtime state, or OpenSpec configuration was changed by creating this snapshot.
