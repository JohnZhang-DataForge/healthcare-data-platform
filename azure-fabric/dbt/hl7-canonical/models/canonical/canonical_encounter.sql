{{ config(materialized='table', file_format='delta') }}
-- Contract encounter-v1.json: exact 27 field order and types; candidate only.
select
    source_encounter_id, source_person_id,
    cast(event_datetime_utc as timestamp) as start_datetime,
    cast(discharge_datetime_utc as timestamp) as end_datetime,
    encounter_class, source_code,
    cast(null as string) as source_description,
    cast(null as string) as source_organization_id,
    cast(null as string) as source_provider_id,
    cast(null as string) as source_payer_id,
    cast(null as decimal(18,2)) as base_encounter_cost,
    cast(null as decimal(18,2)) as total_claim_cost,
    cast(null as decimal(18,2)) as payer_coverage,
    cast(null as string) as reason_code,
    cast(null as string) as reason_description,
    source_system, source_version, source_batch_id,
    cast(source_ingest_date as date) as source_ingest_date,
    source_file, source_file_sha256,
    cast(source_file_size_bytes as bigint) as source_file_size_bytes,
    adapter_name, adapter_version, canonical_version,
    processing_run_id, cast(processed_at as timestamp) as processed_at
from {{ ref('int_hl7_encounter_pairs') }}

