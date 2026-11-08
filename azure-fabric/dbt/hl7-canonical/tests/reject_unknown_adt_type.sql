select message_control_id from {{ source('oie_v2', 'hl7_events') }}
where event_type is null or event_type not in ('A01', 'A03')

