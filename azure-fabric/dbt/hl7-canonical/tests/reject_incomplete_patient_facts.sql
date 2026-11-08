select message_control_id from {{ source('oie_v2', 'hl7_events') }}
where source_system is null or source_batch_id is null
 or source_person_id is null or source_encounter_id is null
 or birth_date is null or gender_code is null
 or race_code is null or ethnicity_code is null
 or source_file_sha256 is null or message_control_id is null

