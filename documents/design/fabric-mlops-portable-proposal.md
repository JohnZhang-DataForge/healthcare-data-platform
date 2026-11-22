# Fabric-first MLOps Exploration with Local Portability — Design Proposal (DRAFT)

Status: **Discussion only — not approved for implementation or merge**. Date: 2026-11-22. Base: main.

## 1. Business purpose
Use remaining Fabric trial to validate an end-to-end reproducible healthcare-data ML workflow, while keeping local Kubernetes as the sustainable long-term execution environment. Synthetic data only; not clinical decision support or patient risk prediction in real care. This is a separate business capability from expanding OMOP clinical tables. Do not require clinical table expansion before the first experiment.

## 2. Initial use case and target validity
Start with a **synthetic visit-utilization classification or regression demo**, using OMOP PERSON and VISIT_OCCURRENCE. Predict a *future-window* synthetic visit count or repeat-visit indicator from features available at a fixed index date. Define cohort eligibility, lookback window (e.g., 180 days), prediction window (e.g., next 30 days), censoring and outcome ascertainment. Random row splits are prohibited because they leak repeated-person information; prefer patient-disjoint and temporal holdout, and explicitly check temporal coverage. If current tiny 4–8 patient Fabric Gold fixtures cannot support a meaningful model, generate a larger deterministic Synthea dataset or use the local larger OMOP dataset; report insufficient sample honestly. Synthetic model metrics are technical demonstration only.

## 3. Architecture and portability
OMOP Gold (Fabric Warehouse or local PostgreSQL) → SQL-based feature extraction with backend adapters → versioned Parquet feature snapshot → Python/Spark training → MLflow experiment tracking → model artifact + metadata → batch scoring → separate prediction output store. Core feature definitions, transformations, training, metrics and model signature should be portable; isolate Fabric Notebook bootstrap, Warehouse connector and MLflow workspace integrations from model business code. Do not write predicted labels into clinical OMOP fact tables. ATLAS remains OHDSI research UI, not MLOps serving layer.

## 4. Fabric trial exploration
- Verify actual Fabric workspace runtime and supported MLflow integration, experiment/model registration APIs and permissions before assuming features exist.
- Build reproducible notebook thin orchestration around importable Python modules; pin Python and library versions.
- Read OMOP Warehouse through supported connector, materialize a feature snapshot with stable dataset fingerprint.
- Log MLflow run: dataset hash, SQL/feature version, code SHA, train/test split strategy, params, metrics, model signature and artifacts.
- Compare baseline (constant/majority), simple interpretable classifier/regressor, and optionally Spark ML implementation; do not optimize on tiny synthetic samples.
- Write scored records to an isolated schema/table with model version, feature snapshot ID, prediction timestamp, batch ID and lineage. Define retention and deletion.
- Independent readback verifies prediction counts, key uniqueness and rerun idempotency.

## 5. Local execution route
Reuse existing K8s, Airflow, Spark, SeaweedFS S3 and PostgreSQL. Deploy lightweight self-hosted MLflow tracking/model registry (backing PostgreSQL and S3) only after checking resource/storage/security needs; MLflow registry capabilities depend on backend configuration. Run training as Kubernetes Job; schedule with Airflow; run batch inference first. Online inference (FastAPI or KServe) is optional and requires an explicit use case. Ensure model files and MLflow metadata can be exported/imported independently of Fabric trial.

## 6. ML governance and evaluation
Feature timestamps strictly before index date; outcome strictly after. Person-disjoint train/validation/test; temporal out-of-time validation where data permits. Assess class balance, AUROC/PR-AUC for classification or MAE/RMSE for counts, calibration, missingness, cohort shift and label leakage. Track all experiments with versioned input data and deterministic seed. No claim of medical efficacy, fairness, generalizability or clinical readiness based on synthetic data. No real PHI, secrets in notebooks or unrestricted public endpoints.

## 7. Milestones and acceptance
M1: Fabric feasibility inventory (MLflow support, runtime, permissions, Warehouse access, synthetic cohort size), cost and limitations documented.
M2: Reproducible baseline training with immutable feature snapshot, run metadata, model artifact and independent rerun.
M3: Fabric batch inference and physical prediction readback; idempotent replay and negative tests.
M4: Same feature contract and training module run locally with equivalent dataset; record expected numerical tolerance and portability gaps.
M5: Add Condition/Measurement/Drug features as the clinical-domain track delivers accepted Gold tables; compare to baseline without redefining target.
M6 (optional): online inference, model monitoring/drift, automated retraining with approval gates.

## 8. Compute and trial cost
Trial capacity remains available; Spark sessions should end after jobs. After trial, do NOT assume Fabric capacity stays available. Preferred long-term: local scheduled batch ML; optional paid F SKU only when needed, using an external Resume → sync/train → verify → Pause controller with timeout and failure-safe cleanup. A paused capacity is not the same as a stopped notebook session; storage and other Azure charges can remain. Avoid expensive always-on serving or heavyweight Kubeflow for the first release. Data is synthetic and regenerable; prioritize preserving source code, experiment configs, feature definitions, model artifacts and evaluation evidence.

## 9. Interfaces to OMOP expansion
Consumer contract: published schema version, stable person/visit keys, feature as-of timestamp, vocabulary/version metadata, DQ status and batch watermark. Do not read uncommitted Candidate tables. ML job should skip or fail closed if upstream publication/readback is incomplete. New clinical domain feature sets are opt-in and independently versioned; a changed mapping requires a new feature snapshot and model run.

## 10. Decisions for review
D1: First target: 30-day repeat visit vs visit count? Is temporal coverage sufficient for either?
D2: Fabric-native MLflow experiment/model registry vs external MLflow as system of record?
D3: First release batch inference only (recommended), or include online API?
D4: How much Fabric synthetic data should be regenerated for credible technical evaluation?
D5: MLflow registry storage and export strategy; local resource budget (CPU/GPU/memory).
D6: Is daily sync exclusively for data publication, with ML training less frequent/on demand?
D7: Minimum acceptance metrics: reproducibility and leakage checks first, predictive score second.

**No code, deployment, workflow execution, PR merge or production data changes authorized by this document.**
