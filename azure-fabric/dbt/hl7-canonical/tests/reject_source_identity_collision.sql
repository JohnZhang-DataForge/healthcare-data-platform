select source_system, source_batch_id, source_encounter_id
from {{ source('oie_v2', 'hl7_events') }}
group by source_system, source_batch_id, source_encounter_id
having count(distinct source_person_id) > 1

