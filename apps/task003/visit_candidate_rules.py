"""Pure-Python rules for TASK003 Encounter -> Visit Candidate (no I/O)."""

DEFERRED_FIELDS = (
    'provider_id', 'care_site_id', 'admitted_from_concept_id',
    'admitted_from_source_value', 'discharged_to_concept_id',
    'discharged_to_source_value', 'preceding_visit_occurrence_id',
)
PRESERVED_SOURCE = (
    'source_code', 'source_description', 'source_organization_id',
    'source_provider_id', 'source_payer_id', 'reason_code',
    'reason_description',
)


def validate_rules(mapping, raw_contract, candidate_contract):
    if mapping.get('visit_model', {}).get('mode') != 'one_source_encounter_per_visit_occurrence':
        raise ValueError('Unexpected Visit cardinality')
    if mapping['visit_model'].get('aggregation') is not False:
        raise ValueError('Aggregation is not supported')
    if mapping['visit_model'].get('stable_id_map') != 'etl.visit_occurrence_id_map':
        raise ValueError('Unexpected Visit ID map')
    if mapping.get('source_system') != 'synthea' or mapping.get('source_version') != 'v3.3.0':
        raise ValueError('Unexpected source contract')
    if mapping.get('visit_source_value') != 'encounter_class':
        raise ValueError('visit_source_value must use encounter_class')
    if mapping.get('visit_source_concept_id') is not None:
        raise ValueError('visit_source_concept_id must remain NULL')
    if mapping.get('visit_type_concept_id') != 32827:
        raise ValueError('Unexpected visit type concept')
    if tuple(mapping.get('deferred_target_fields', ())) != DEFERRED_FIELDS:
        raise ValueError('Deferred target fields changed')
    if tuple(mapping.get('source_fields_preserved_for_future_mapping', ())) != PRESERVED_SOURCE:
        raise ValueError('Preserved source fields changed')

    if raw_contract.get('entity') != 'encounter' or raw_contract.get('canonical_version') != 'v1':
        raise ValueError('Unexpected canonical Encounter contract')
    raw_names = {x['name'] for x in raw_contract['fields']}
    if len(raw_names) != len(raw_contract['fields']):
        raise ValueError('Duplicate Raw field')
    if not set(PRESERVED_SOURCE).issubset(raw_names):
        raise ValueError('Missing preserved Raw source fields')
    if raw_contract.get('primary_key') != ['source_system', 'source_encounter_id']:
        raise ValueError('Unexpected Raw primary key')

    classes = mapping.get('class_to_visit_concept')
    if not isinstance(classes, dict) or set(classes) != set(raw_contract['allowed_encounter_classes']):
        raise ValueError('Raw and Visit class mappings disagree')
    for key, value in classes.items():
        concept = value.get('concept_id') if isinstance(value, dict) else None
        if type(concept) is not int or concept <= 0:
            raise ValueError('Invalid Visit concept for ' + key)

    if candidate_contract.get('contract_version') != 'v1':
        raise ValueError('Unknown candidate contract version')
    if candidate_contract.get('target_table') != 'cdm.visit_occurrence':
        raise ValueError('Unexpected target table')
    if candidate_contract.get('visit_occurrence_id_allocated') is not False:
        raise ValueError('Candidate must not allocate Visit ID')
    if candidate_contract.get('publish_status') != 'NOT_PUBLISHED':
        raise ValueError('Candidate source must not claim to be published')
    if candidate_contract.get('primary_key') != ['source_system', 'source_encounter_id']:
        raise ValueError('Unexpected candidate key')

    fields = candidate_contract['fields']
    names = [item['name'] for item in fields]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate candidate field')
    if 'visit_occurrence_id' in names:
        raise ValueError('Premature Visit ID in candidate schema')
    if not {'person_id', 'visit_concept_id', 'visit_start_date',
            'visit_end_date', 'visit_type_concept_id'}.issubset(names):
        raise ValueError('Missing required OMOP Visit fields')
    if not set(DEFERRED_FIELDS).issubset(names):
        raise ValueError('Missing nullable deferred Visit fields')
    if not set(PRESERVED_SOURCE).issubset(names):
        raise ValueError('Missing preserved source field')
    if not set(names).issubset(raw_names | {
        'person_id', 'raw_publish_run_id', 'visit_concept_id',
        'visit_start_date', 'visit_start_datetime',
        'visit_end_date', 'visit_end_datetime', 'visit_type_concept_id',
        'visit_source_value', 'visit_source_concept_id',
        *DEFERRED_FIELDS,
    }):
        raise ValueError('Unexpected candidate field')
    valid_types = {'string', 'integer', 'date', 'timestamp', 'long'}
    for item in fields:
        if item.get('type') not in valid_types or type(item.get('nullable')) is not bool:
            raise ValueError('Invalid candidate schema field')
        if item['name'] in DEFERRED_FIELDS and item['nullable'] is not True:
            raise ValueError('Deferred field must be nullable')
    return {key: value['concept_id'] for key, value in classes.items()}
