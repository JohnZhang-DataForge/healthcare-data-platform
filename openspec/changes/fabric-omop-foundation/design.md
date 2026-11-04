# Design — Fabric OMOP Foundation

## 1. Boundaries and deployment ownership

- Existing Workspace: `healthcare-omop`; user-created Warehouse: `dw-omop-5.4` (do not recreate).
- Existing Lakehouse `lh_omop_analytics`: Bronze, Silver, Approved and G5 Candidate remain Delta tables **in the same Lakehouse**. No second staging Lakehouse and no extra Blob roundtrip.
- Warehouse Gold: `cdm.*` for **official OHDSI CDM 5.4**; `etl.*` for stable identity mapping, batch fence and idempotency ledger; `audit.*` for independent reconciliation.
- Shared Engine: pure transformations without Fabric/Local PG I/O. The Fabric writer MUST NOT reach Local DP Postgres, Local ID Map or local vocabulary at runtime.
- Git-first: Terraform only for provisioning infrastructure not already created. SQL project / migrations manage Warehouse schema; authenticated Self-Runner applies approved schema and verifies independent SQL readback. Fabric Pipeline later orchestrates Spark Candidate → Warehouse Commit.
- Warehouse service does not execute SQL or expose TDS when Capacity is paused. F0 probe MUST NOT resume Capacity automatically.

## 2. F0 read-only permission and endpoint probe

Fixed server supplied by user:
`5acjvcj5rvwercfbppplelk7di-hpqfy5fwcvyermhfrrlvbkqy3q.datawarehouse.fabric.microsoft.com`, TCP 1433, Initial Catalog `dw-omop-5.4`.

A separate Self-Runner GitHub Actions workflow, main-branch-only and explicitly dispatched, MUST:
1. Pin the checked-out controller code to Self-Runner main and refuse PR code execution in privileged jobs.
2. Use GitHub OIDC federated assertion (no Client Secret) for existing `FABRIC_CLIENT_ID`/`FABRIC_TENANT_ID`; obtain Fabric REST and SQL resource tokens with distinct audiences.
3. GET exact Warehouse item from Workspace by its fixed GUID `745ce03b-15b6-4870-b0e5-8c5750aa18dc`, matching item type/name (GET only).
4. Connect with SQL Server TDS, encryption and `DATABASE=dw-omop-5.4`; execute a **fixed SELECT only** returning DB_NAME(), CURRENT_USER and 1. No arbitrary SQL inputs.
5. Check result database exactly; output diagnostic category, not tokens, assertion, connection details or row data. Driver missing, network, capacity, service principal permission and catalog mismatch are distinct HOLD outcomes.

A successful Fabric REST GET does **not** imply SQL endpoint permission. SQL probe SUCCESS does **not** imply CDM schema exists.

## 3. F0 schema

- Follow official OHDSI `CommonDataModel` v5.4 definitions, full column/type/nullability list, no invented abbreviated Person/Visit tables. Record source tag/commit, schema version, checksum and executed deployment SHA.
- Compile SQL Project and review DacFx drift plan before applying. Initial readback includes `sys.schemas`, `sys.tables`, `sys.columns`, type/nullability and CDM 5.4 inventory; schema deploy remains separate from first connectivity probe.
- Fabric Warehouse PK/FK/UNIQUE constraints may not be enforced: implement explicit DQ and identity uniqueness checks; do not assume PG-like enforcement.

## 4. F1–F3 boundaries

- F1: `etl.identity_map` uses immutable hospital/source patient and encounter keys with documented scope and stable assigned OMOP IDs. Vocabulary requires official concept IDs and matching release metadata/validity; fail closed on unknown concepts.
- F2: Spark Candidate generation can materialize same Lakehouse Delta for reproducibility. Gold writes in Warehouse use a single controlled transaction (identity, Person/Visit, ledger) with explicit commit fence and replay skip.
- F3: exact approved G4 request/manifest/processing hash; 100 Patient / 5,918 Encounter source input count does not assert equivalent `visit_occurrence` row count unless mapping/DQ justify it. Independent SQL readback checks person/visit IDs, FK, DQ, replay and ledger.
- No new Fabric Workspace, no Local PG runtime dependency, no edits to G5 `nb_fhir_ingest` / `pl_fhir_ingest` in this Change.

## 5. Security and operations

Never store identity tokens, secrets or synthetic PHI in repository/logs. On unknown shared runtime contention or Capacity state, HOLD rather than resume or force-write. A Portal-created Warehouse must not be represented as Terraform state-managed; any future import is a separately reviewed action. Fabric workspace Git sync of an `Added` Warehouse item can affect other items, so no unrestricted UpdateAll; review drift before incorporating its native definition.

Official references:
- https://learn.microsoft.com/en-us/fabric/data-warehouse/connectivity
- https://learn.microsoft.com/en-us/fabric/data-warehouse/service-principals
- https://learn.microsoft.com/en-us/fabric/data-warehouse/git-integration
- https://github.com/OHDSI/CommonDataModel

## 6. Acceptance evidence

Distinguish SOURCE/STATIC_PASS, REST_VISIBLE, SQL_SELECT_PASS, SCHEMA_DEPLOYED, SCHEMA_READBACK_PASS, GOLD_COMMITTED and REPLAY_PASS. Record Git SHA, Actions Run ID, actual observed object IDs and checksums. Do not infer later gates from earlier status.

## 7. F1 Blob-to-Warehouse vocabulary first-load implementation

- Direct source: private Azure Storage `johnzhang.blob.core.windows.net/omop-vocabulary` root, exactly nine OHDSI Athena tab-separated CSVs. No new Lakehouse or Terraform-managed DW resource. Pin names / byte size / SHA256 (verified by independent 9/9 scan), inspect header field names/order against official CDM 5.4 schema, and match source ETag around COPY.
- Self-Runner authenticates using existing Entra/GitHub federated OIDC. SQL token audience `https://database.windows.net/.default`; the same principal has independent Azure Storage Blob Data Reader authorization. Never use account keys or log tokens/SAS.
- Use native Fabric Warehouse `COPY INTO cdm.<allowlisted_table>` with `FILE_TYPE='CSV'`, `FIRSTROW=2`, `FIELDTERMINATOR='0x09'`, `ROWTERMINATOR='0x0A'`, `FIELDQUOTE='"'` and `MAXERRORS=0`. No FHIR Pipeline involvement.
- Stream source TSV using a strict CSV parser to obtain exact row count, ensure correct column count, issue a single COPY statement per table, then separately establish a new SQL connection for exact COUNT_BIG comparison. Non-empty target is accepted only as a replay SKIP if its count exactly matches immutable source; otherwise HOLD, no TRUNCATE/DROP/DELETE and no blind retry.
- Pilot first uses four small tables; only after live verification does a separate PR switch to all nine. After all-nine readback, validate Concept ID uniqueness, vocabulary ID uniqueness, Concept validity dates and version; only then close task 1.2. A successful COPY is **not** by itself proof of complete domain correctness or an enforced FK.

## 8. F1 Identity Map design (Source contract and Fabric constraints)

- Canonical Person source key is `(hospital_id, source_system, source_record_id)`; Encounter is `(hospital_id, source_system, source_encounter_id)`. `source_system` must remain stable across FHIR and CSV for the same *logical* source; if identity normalization across feeds is not proven, **do not merge entities by name/DOB**.
- `etl.identity_map` records `entity_type` (only `PERSON` or `VISIT_OCCURRENCE`), full source key, positive `omop_id INT`, first batch and mapping_version; `etl.id_allocator` holds a Warehouse-global next INT per entity, not per hospital. `etl.batch_ledger` fences exact manifest and mapping hashes. `audit` stores reconciliation counts and vocabulary file provenance.
- **No automatic Fabric `IDENTITY` for official Person/Visit IDs:** Fabric Warehouse only supports BIGINT IDENTITY, while CDM 5.4 Person/Visit IDs are INT. Explicitly validate 1..2,147,483,647 overflow bounds and dense candidate-to-map FK resolution; source IDs and hash/modulo are forbidden as surrogate OMOP IDs.
- Snapshot isolation is always applied by Fabric Warehouse even if T-SQL requests higher isolation. F2 writer must be single-writer within target Warehouse, use an explicit atomic transaction for allocator+ID map+Person+Visit+committed ledger, verify collisions and treat write conflicts as HOLD or bounded replay-safe retry. Do not claim SQL constraints are enforced.
- The current change only creates versioned **empty-schema source**; independent migration readback and real Person/Visit Writer are separate acceptance gates.

## 9. Observed F1 state after physical acceptance (2026-11-04)

- The five ETL/Audit table DDL definitions were genuinely applied and independently read back PASS in [Self-Runner #41820260817](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820260817). They were empty, not a functioning ID allocator or ledger yet.
- Vocabulary DQ (real [#41820573379](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820573379)) found zero missing references in eleven distinct joins over the complete nine-table export; date and reverse relationship checks also PASS. Twenty-eight `vocabulary_version` values are blank, requiring separate release and licensed terminology review. Never fill with fabricated version values.
- The next gate is F2: prove allocation under Warehouse snapshot isolation, Person/Visit FK resolution, and exact batch manifest Replay. No automated F1 schema run authorized business writes.
