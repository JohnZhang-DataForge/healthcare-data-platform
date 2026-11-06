# Design: exact Batch attestation in existing Discovery Pod

## Existing boundaries

`apps/landing_discovery/scan_ready_batches.py` validates each S3 manifest, quarantines incompatible legacy records, enforces unique source/Batch identities, and returns the complete validated ready inventory (bounded by `MAX_MANIFESTS=1000`).

`apps/landing_discovery/run_airflow_scan.py` limits the Airflow XCom preview to 25 rows. The preview is explicitly documented as *non-authoritative*. `new_only_omop_routing.select_verified_new_only` currently demands `preview_truncated=False` and `ready_count==len(preview)`, wrongly using a display-size bound as a processing bound.

## Minimal implementation

1. `new_only_omop_consumer` passes manual Run Conf's Batch ID, Manifest URI, SHA256 to the existing `scan_ready_manifests` KubernetesPodOperator using templated CLI arguments; it already has read-only S3 secrets. Neither PythonOperator nor Airflow scheduler gains S3 credentials.
2. `run_airflow_scan` continues the exact same source scan. Before serializing XCom it finds the requested Batch in **full validated inventory** and confirms the requested Manifest URI/SHA and `synthea/v3.3.0/INTAKE_VERIFIED/18` row identity. Reject missing, partial or drifted requests. Add `verified_selected_batch` to the otherwise unchanged preview summary.
3. The downstream Python routing function validates Run Conf shape, manual-only, SHA, URI, discovery read-only/status metadata and preview self-consistency. It requires `verified_selected_batch` and checks the selected identity against Run Conf and expected Manifest status. **It never selects from `ready_batches_preview`**, even when `preview_truncated=True`.
4. Existing read-only PG Claim lookup, manual Spark/Writer approval and physical DB credential gates are unchanged. Standalone scheduled Discovery DAG calls the same scanner with no manual target, retaining previous behavior.
5. Once real E2E passes, separate commit modifies just `MAX_XCOM_PREVIEW=100` and its display tests; main business routing does not change.

## Tradeoffs

This deliberately does **not** optimize the global scan or remove its 1,000-manifest cap, because the approved fix is the preview-vs-selection bug. Later scale improvements can add exact S3 GetObject without whole-list scans if necessary; this change preserves original duplicate-manifest global detection.

XCom remains bounded by 25 rows before display update, 100 after. The single verified target may be in addition to the displayed list; it is only 1 metadata record and has no claim authorization.

## Verification

Contract tests: below-cap and over-cap XCom; exact target at index 26 (outside preview); 101 rows with 100-item preview; rejected missing target, mismatched URI/SHA, malformed/conflicting metadata, missing attestation; scheduled preview-only unchanged. CI full Discovery/DAG sources, OpenSpec and image PR validation, Main publish. Real S3/PG E2E with preserved existing three Synthea READY Batches documented in [three-Batch evidence](../fix-multi-parquet-omop-writer-read/evidence/THREE-FRESH-SYNTHEA-BATCHES-20261021.md); no data cleanup.
