{{ config(materialized='table', file_format='delta') }}

-- An A01 alone cannot produce the current v1 completed Encounter.
with events as (
    select *, row_number() over (
       partition by source_system, source_encounter_id, event_type
       order by message_control_id
    ) as rn from {{ source('oie_v2', 'hl7_events') }}
),
admitted as (select * from events where event_type='A01' and rn=1),
discharged as (select * from events where event_type='A03' and rn=1)
select
    a.source_encounter_id, a.source_person_id,
    cast(a.event_datetime_utc as timestamp) as start_datetime,
    cast(d.event_datetime_utc as timestamp) as end_datetime,
    'inpatient' as encounter_class,
    a.source_code, cast(null as string) as source_description,
    cast(null as string) as source_organization_id,
    cast(null as string) as source_provider_id,
    cast(null as string) as source_payer_id,
    cast(null as decimal(18,2)) as base_encounter_cost,
    cast(null as decimal(18,2)) as total_claim_cost,
    cast(null as decimal(18,2)) as payer_coverage,
    cast(null as string) as reason_code,
    cast(null as string) as reason_description,
    a.source_system, a.source_version, a.source_batch_id,
    cast(a.source_ingest_date as date) as source_ingest_date,
    a.source_file, a.source_file_sha256,
    cast(a.source_file_size_bytes as bigint) as source_file_size_bytes,
    a.adapter_name, a.adapter_version, a.canonical_version,
    a.processing_run_id, cast(a.processed_at as timestamp) as processed_at
from admitted a inner join discharged d
on a.source_system=d.source_system and a.source_encounter_id=d.source_encounter_id
and a.source_person_id=d.source_person_id and a.source_batch_id=d.source_batch_id
where cast(a.event_datetime_utc as timestamp) <= cast(d.event_datetime_utc as timestamp)
