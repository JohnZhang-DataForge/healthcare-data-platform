select source_system, source_batch_id, message_control_id
from {{ source('oie_v2', 'hl7_events') }}
group by source_system, source_batch_id, message_control_id
having count(*) > 1

