select source_system, source_encounter_id
from {{ ref('canonical_encounter') }}
group by source_system, source_encounter_id having count(*) > 1

