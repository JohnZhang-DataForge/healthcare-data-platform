{{ config(materialized='table', file_format='delta') }}
-- Contract patient-v1.json: exact 18 field order and types; candidate only.
select
    source_person_id as source_record_id,
    cast(birth_date as date) as birth_date,
    cast(null as date) as death_date,
    gender_code, race_code, ethnicity_code, source_system,
    source_version, source_batch_id, cast(source_ingest_date as date) as source_ingest_date,
    source_file, source_file_sha256, cast(source_file_size_bytes as bigint) as source_file_size_bytes,
    adapter_name, adapter_version, canonical_version,
    processing_run_id, cast(processed_at as timestamp) as processed_at
from {{ ref('int_hl7_patient_latest') }}

