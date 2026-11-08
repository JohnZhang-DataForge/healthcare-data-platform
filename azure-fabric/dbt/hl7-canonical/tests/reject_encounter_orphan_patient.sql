select e.source_system, e.source_encounter_id
from {{ ref('canonical_encounter') }} e
left join {{ ref('canonical_patient') }} p
 on e.source_system=p.source_system and e.source_person_id=p.source_record_id
where p.source_record_id is null

