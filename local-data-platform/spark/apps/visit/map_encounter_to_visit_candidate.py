"""Pure PySpark DataFrame transform. No Spark job startup or storage writes.

The caller must verify APPROVED Raw, pinned contracts, JDBC Person mapping,
concept validity and counts before publishing the returned candidate DataFrame.
"""


DEFERRED_TYPES = {
    'provider_id': 'int', 'care_site_id': 'int',
    'visit_source_concept_id': 'int',
    'admitted_from_concept_id': 'int',
    'admitted_from_source_value': 'string',
    'discharged_to_concept_id': 'int',
    'discharged_to_source_value': 'string',
    'preceding_visit_occurrence_id': 'int',
}


def map_encounter_to_candidate(raw, persons, mapping, context):
    """Return one unapproved candidate row per raw Encounter; no I/O or writes.

    persons must contain source_system, source_person_id, person_id.
    The caller must verify the Person map/CDM FK and one-to-one join.
    """
    from pyspark.sql import functions as F

    if context['mapping_contract_sha256'] is None:
        raise ValueError('Missing pinned mapping contract SHA')
    mapping_ids = mapping['class_to_visit_concept']
    pairs = []
    for klass, info in sorted(mapping_ids.items()):
        pairs.extend((F.lit(klass), F.lit(info['concept_id'])))
    visit_concept = F.element_at(F.create_map(*pairs), F.col('encounter_class'))

    person_reference = persons.select('source_system', 'source_person_id', 'person_id')
    joined = raw.join(
        person_reference, ['source_system', 'source_person_id'], 'left'
    )
    fields = [
        F.col('source_system'),
        F.col('source_encounter_id'),
        F.col('source_person_id'),
        F.col('person_id').cast('int').alias('person_id'),
        visit_concept.cast('int').alias('visit_concept_id'),
        F.to_date('start_datetime').alias('visit_start_date'),
        F.col('start_datetime').cast('timestamp').alias('visit_start_datetime'),
        F.to_date('end_datetime').alias('visit_end_date'),
        F.col('end_datetime').cast('timestamp').alias('visit_end_datetime'),
        F.lit(mapping['visit_type_concept_id']).cast('int').alias('visit_type_concept_id'),
        F.lit(None).cast('int').alias('provider_id'),
        F.lit(None).cast('int').alias('care_site_id'),
        F.col('encounter_class').alias('visit_source_value'),
        F.lit(None).cast('int').alias('visit_source_concept_id'),
        F.lit(None).cast('int').alias('admitted_from_concept_id'),
        F.lit(None).cast('string').alias('admitted_from_source_value'),
        F.lit(None).cast('int').alias('discharged_to_concept_id'),
        F.lit(None).cast('string').alias('discharged_to_source_value'),
        F.lit(None).cast('int').alias('preceding_visit_occurrence_id'),
        F.col('encounter_class'),
        F.col('source_code'),
        F.col('source_description'),
        F.col('source_organization_id'),
        F.col('source_provider_id'),
        F.col('source_payer_id'),
        F.col('reason_code'),
        F.col('reason_description'),
        F.col('source_version'),
        F.col('source_batch_id'),
        F.col('source_ingest_date'),
        F.col('processing_run_id'),
        F.lit(context['raw_publish_run_id']).alias('raw_publish_run_id'),
        F.col('canonical_version'),
        F.col('source_file'),
        F.col('source_file_sha256'),
        F.col('source_file_size_bytes'),
    ]
    return joined.select(*fields)
