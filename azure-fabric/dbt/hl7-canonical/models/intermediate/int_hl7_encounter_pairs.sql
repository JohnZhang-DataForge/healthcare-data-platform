-- A01 alone cannot produce a completed v1 Encounter.
with ranked as (
    select *, row_number() over (
        partition by source_system, source_batch_id, source_encounter_id,
                     source_person_id, event_type
        order by message_control_id
    ) as rn
    from {{ ref('stg_hl7_events') }}
    where event_type in ('A01', 'A03')
), admitted as (
    select * from ranked where event_type = 'A01' and rn = 1
), discharged as (
    select * from ranked where event_type = 'A03' and rn = 1
)
select a.*, d.event_datetime_utc as discharge_datetime_utc
from admitted a join discharged d
  on a.source_system = d.source_system
 and a.source_batch_id = d.source_batch_id
 and a.source_encounter_id = d.source_encounter_id
 and a.source_person_id = d.source_person_id
where a.event_datetime_utc <= d.event_datetime_utc

