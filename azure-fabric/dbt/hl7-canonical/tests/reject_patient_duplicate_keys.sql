select source_system, source_record_id
from {{ ref('canonical_patient') }}
group by source_system, source_record_id having count(*) > 1

