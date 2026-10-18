"""Read-only Spark validation of approved Encounter Raw and Person references."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from pyspark.sql import SparkSession, functions as F
from canonical_gate import validate_contract, validate_metadata, validate_unique_key
from verify_encounter_remote_metadata import verify_metadata


def main():
    directory = Path(__file__).resolve().parent
    context = json.loads((directory / 'input-context.json').read_bytes())
    contracts = {}
    for filename, key in (
        ('encounter-v1.json', 'canonical_contract_sha256'),
        ('visit-class-v1.json', 'mapping_contract_sha256'),
    ):
        data = (directory / filename).read_bytes()
        if hashlib.sha256(data).hexdigest() != context[key]:
            raise ValueError('Mounted contract SHA mismatch: ' + filename)
        contracts[filename] = json.loads(data)

    spark = SparkSession.builder.appName('visit-raw-preflight').config(
        'spark.sql.session.timeZone', 'UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')

    try:
        def remote_bytes(uri):
            rows = spark.read.format('binaryFile').load(
                uri.replace('s3://', 's3a://', 1)
            ).select('content').collect()
            if len(rows) != 1:
                raise ValueError('Expected exactly one remote metadata object')
            return bytes(rows[0]['content'])

        mb = remote_bytes(context['raw_manifest_uri'])
        db = remote_bytes(context['dq_uri'])
        verify_metadata(context, mb, db)
        manifest = json.loads(mb)

        raw = spark.read.parquet(
            context['raw_data_uri'].replace('s3://', 's3a://', 1)
        ).cache()
        contract = contracts['encounter-v1.json']
        mapping = contracts['visit-class-v1.json']

        validate_contract(raw, contract)
        keys = validate_unique_key(raw, contract['primary_key'])
        if keys['rows'] != context['expected_rows']:
            raise ValueError('Raw row count differs from pinned manifest')

        metadata = dict(
            source_system=context['source'],
            source_version=context['source_version'],
            source_batch_id=context['batch_id'],
            source_ingest_date=context['ingest_date'],
            processing_run_id=context['processing_run_id'],
            source_file=manifest['source_file'],
            source_file_sha256=manifest['source_file_sha256'],
            source_file_size_bytes=manifest['source_file_size_bytes'],
            adapter_name='synthea_encounter_adapter',
            adapter_version='v1',
            canonical_version='v1',
        )
        validate_metadata(raw, metadata)

        for name in ('source_encounter_id', 'source_person_id', 'encounter_class'):
            if raw.filter(F.length(F.trim(F.col(name))) == 0).limit(1).count():
                raise ValueError('Blank required key/class: ' + name)

        if raw.filter(F.length(F.col('source_encounter_id')) > 255).limit(1).count():
            raise ValueError('Encounter key exceeds stable map column length')

        if raw.filter(
            F.col('end_datetime') < F.col('start_datetime')
        ).limit(1).count():
            raise ValueError('Encounter end precedes start')

        counts = {
            r['encounter_class']: r['count']
            for r in raw.groupBy('encounter_class').count().collect()
        }
        if set(counts) - set(mapping['class_to_visit_concept']):
            raise ValueError('Unmapped encounter class')

        if os.environ['PGDATABASE'] != 'omop':
            raise ValueError('Unexpected PostgreSQL database')

        def query(sql):
            return (
                spark.read.format('jdbc')
                .option(
                    'url',
                    'jdbc:postgresql://' + os.environ['PGHOST'] + ':'
                    + os.environ['PGPORT'] + '/' + os.environ['PGDATABASE'],
                )
                .option('user', os.environ['PGUSER'])
                .option('password', os.environ['PGPASSWORD'])
                .option('driver', 'org.postgresql.Driver')
                .option(
                    'sessionInitStatement',
                    'SET default_transaction_read_only = on',
                )
                .option('dbtable', '(' + sql + ') preflight')
                .load()
            )

        persons = query("""
            SELECT m.source_system, m.source_person_id, m.person_id,
                   p.person_id AS cdm_person_id
            FROM etl.person_id_map m
            LEFT JOIN cdm.person p ON p.person_id = m.person_id
            WHERE m.source_system = 'synthea'
        """).cache()

        joined = raw.join(
            persons, ['source_system', 'source_person_id'], 'left'
        ).cache()

        if joined.count() != keys['rows']:
            raise ValueError('Person join inflated Encounter rows')

        if joined.filter(
            F.col('person_id').isNull()
            | F.col('cdm_person_id').isNull()
            | (F.col('person_id') <= 0)
        ).limit(1).count():
            raise ValueError('Encounter lacks valid Person map/CDM reference')

        used_people = joined.select('person_id').distinct().count()
        domains = {
            v['concept_id']: 'Visit'
            for v in mapping['class_to_visit_concept'].values()
        }
        domains[mapping['visit_type_concept_id']] = 'Type Concept'
        if any(type(k) is not int or k <= 0 for k in domains):
            raise ValueError('Invalid mapped concept IDs')

        concepts = query(
            'SELECT concept_id, domain_id, standard_concept, invalid_reason, '
            'valid_start_date, valid_end_date FROM cdm.concept WHERE concept_id IN ('
            + ','.join(map(str, sorted(domains))) + ')'
        ).collect()

        if {r['concept_id'] for r in concepts} != set(domains):
            raise ValueError('Missing mapped concepts')

        for r in concepts:
            if (
                r['domain_id'] != domains[r['concept_id']]
                or r['standard_concept'] != 'S'
                or r['invalid_reason'] is not None
                or not (
                    r['valid_start_date']
                    <= datetime.now(timezone.utc).date()
                    <= r['valid_end_date']
                )
            ):
                raise ValueError('Invalid mapped concept: ' + str(r['concept_id']))

        # Recheck metadata pins before emitting successful validation evidence.
        verify_metadata(
            context,
            remote_bytes(context['raw_manifest_uri']),
            remote_bytes(context['dq_uri']),
        )
        result = dict(
            status='PASS',
            raw_rows=keys['rows'],
            raw_unique_keys=keys['unique_keys'],
            referenced_persons=used_people,
            encounter_classes=counts,
            raw_publish_run_id=context['raw_publish_run_id'],
            raw_manifest_sha256=context['raw_manifest_sha256'],
            dq_sha256=context['dq_sha256'],
            canonical_contract_sha256=context['canonical_contract_sha256'],
            mapping_contract_sha256=context['mapping_contract_sha256'],
            raw_schema='PASS',
            raw_metadata='PASS',
            person_references='PASS',
            concepts='PASS',
            postgresql_write=False,
            s3_write=False,
        )
        print(
            'VISIT_RAW_PREFLIGHT_RESULT=' + json.dumps(result, sort_keys=True),
            flush=True,
        )
    finally:
        spark.stop()


if __name__ == '__main__':
    main()
