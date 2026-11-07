{{ config(materialized='table', file_format='delta') }}

-- HL7 source-specific SQL candidate, not a sanctioned Silver publication.
with ranked as (
    select *, row_number() over (
       partition by source_system, source_person_id
       order by event_datetime_utc desc, message_control_id desc
    ) as rn from {{ source('oie_v2', 'hl7_events') }}
)
select
    source_person_id as source_record_id,
    cast(birth_date as date) as birth_date,
    cast(null as date) as death_date,
    gender_code, race_code, ethnicity_code, source_system,
    source_version, source_batch_id, cast(source_ingest_date as date) as source_ingest_date,
    source_file, source_file_sha256,
    cast(source_file_size_bytes as bigint) as source_file_size_bytes,
    adapter_name, adapter_version, canonical_version, processing_run_id,
    cast(processed_at as timestamp) as processed_at
from ranked
where rn = 1 and birth_date is not null and gender_code is not null
and race_code is not null and ethnicity_code is not null
