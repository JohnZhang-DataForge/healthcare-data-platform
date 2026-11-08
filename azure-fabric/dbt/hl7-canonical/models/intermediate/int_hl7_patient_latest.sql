-- Preserve legacy deterministic patient precedence; do not manufacture missing facts.
with ranked as (
    select *, row_number() over (
        partition by source_system, source_person_id
        order by event_datetime_utc desc, message_control_id desc
    ) as rn from {{ ref('stg_hl7_events') }}
)
select * from ranked where rn = 1
    and birth_date is not null and gender_code is not null
    and race_code is not null and ethnicity_code is not null

