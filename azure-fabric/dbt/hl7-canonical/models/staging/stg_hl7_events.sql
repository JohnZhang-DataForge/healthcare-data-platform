-- Source fields originate in the existing verified Python HL7 parser and intake.
select
    source_system, source_version, source_batch_id, source_ingest_date,
    source_file, source_file_sha256, source_file_size_bytes,
    adapter_name, adapter_version, canonical_version,
    processing_run_id, processed_at, message_control_id, event_type,
    source_person_id, source_encounter_id, birth_date, gender_code,
    race_code, ethnicity_code, event_datetime_utc, encounter_class, source_code
from {{ source('oie_v2', 'hl7_events') }}

