select d.message_control_id
from {{ source('oie_v2', 'hl7_events') }} d
join {{ source('oie_v2', 'hl7_events') }} a
  on a.event_type = 'A01' and d.event_type = 'A03'
 and a.source_system = d.source_system
 and a.source_batch_id = d.source_batch_id
 and a.source_encounter_id = d.source_encounter_id
 and a.source_person_id = d.source_person_id
where a.event_datetime_utc > d.event_datetime_utc

