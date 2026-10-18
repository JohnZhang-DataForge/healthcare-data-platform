"""TASK003 STEP05G2C2C1 Spark driver. Fail-closed, writes data ONLY.

The later orchestrator must create the immutable lock with `kubectl create`,
re-list the exact empty S3 prefix, snapshot mounted files, then mint a short
permit. Neither this module import nor its local tests starts Spark.
"""
import hashlib
import json
import os
import ssl
from datetime import datetime, timezone
from functools import reduce
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from processed_visit_writer_core import (
    person_snapshot_fingerprint, validate_permit, write_once_with_readback,
)

MOUNTED_SOURCES = (
    'validate_visit_candidate_preflight.py',
    'map_encounter_to_visit_candidate.py',
    'canonical_gate.py',
    'visit_candidate_rules.py',
    'verify_encounter_remote_metadata.py',
    'resolve_approved_encounter_raw.py',
    'encounter-v1.json',
    'visit-class-v1.json',
    'visit-candidate-v1.json',
)
ARTIFACTS = (
    'processed-plan.json', 'processed-write-intent.json',
    'reservation-create.json', 'fresh-s3-listing.json', 'write-permit.json',
    'step05f2-run-state.json',
)
TYPE_NAMES = {'string': 'string', 'integer': 'int', 'long': 'bigint',
              'timestamp': 'timestamp', 'date': 'date'}


def require(test, message):
    if not test:
        raise ValueError('PROCESSED_DRIVER_GUARD: ' + message)


def digest(b):
    return hashlib.sha256(b).hexdigest()


def verify_bundle(directory):
    """Pure check of entire immutable ConfigMap snapshot."""
    spec = json.loads((directory / 'processed-writer-input.json').read_bytes())
    require(spec.get('schema') == 'task003.visit_processed.spark_driver.v1',
            'wrong driver input schema')
    require(spec.get('task') == 'TASK-003', 'wrong task')
    require(spec.get('step') == 'STEP-05G2C2C', 'wrong step')
    require(spec.get('source_file_sha256') is not None, 'missing sources')
    f2 = spec['f2_input']
    expected = f2['mounted_file_sha256']
    require(set(expected) == set(MOUNTED_SOURCES), 'F2 source file inventory drift')
    require(spec['source_file_sha256'] == expected, 'F2 source pins differ')
    hashes = spec.get('artifact_sha256')
    require(isinstance(hashes, dict) and set(hashes) == set(ARTIFACTS),
            'artifact file inventory drift')
    for name, expected_sha in {**expected, **hashes}.items():
        path = directory / name
        require(path.is_file() and not path.is_symlink(),
                'unsafe or missing mounted file: ' + name)
        require(digest(path.read_bytes()) == expected_sha,
                'mounted file changed: ' + name)
    permit = json.loads((directory / 'write-permit.json').read_bytes())
    plan_bytes = (directory / 'processed-plan.json').read_bytes()
    intent_bytes = (directory / 'processed-write-intent.json').read_bytes()
    reservation_bytes = (directory / 'reservation-create.json').read_bytes()
    listing_bytes = (directory / 'fresh-s3-listing.json').read_bytes()
    plan = validate_permit(permit, plan_bytes, intent_bytes,
                           reservation_bytes, listing_bytes)
    intent = json.loads(intent_bytes)
    f2_bytes = (directory / 'step05f2-run-state.json').read_bytes()
    f2_state = json.loads(f2_bytes)
    require(f2_state.get('task') == 'TASK-003' and
            f2_state.get('step') == 'STEP-05F2' and
            f2_state.get('status') == 'PASS', 'F2 evidence not approved')
    require(f2_state['input'] == f2, 'F2 input snapshot drift')
    require(intent.get('step05f2_sha256') == digest(f2_bytes),
            'Write Intent F2 evidence pin')
    require(plan.get('source_f2_evidence_sha256') == digest(f2_bytes),
            'G1 plan F2 evidence pin')
    require(f2_state['result']['candidate_rows'] == plan['expected_rows'] and
            f2_state['result']['referenced_persons'] == plan['expected_persons'],
            'F2 counts changed')
    source_rel_paths = {
        'map_encounter_to_visit_candidate.py':
            'spark/apps/visit/map_encounter_to_visit_candidate.py',
        'validate_visit_candidate_preflight.py':
            'spark/apps/visit/validate_visit_candidate_preflight.py',
        'canonical_gate.py': 'spark/common/canonical_gate.py',
        'visit_candidate_rules.py': 'apps/task003/visit_candidate_rules.py',
        'verify_encounter_remote_metadata.py':
            'apps/task003/verify_encounter_remote_metadata.py',
        'resolve_approved_encounter_raw.py':
            'apps/task003/resolve_approved_encounter_raw.py',
        'encounter-v1.json': 'spark/contracts/canonical/encounter-v1.json',
        'visit-class-v1.json': 'spark/contracts/omop/visit-class-v1.json',
        'visit-candidate-v1.json': 'spark/contracts/omop/visit-candidate-v1.json',
    }
    for name, rel in source_rel_paths.items():
        require(intent['source_sha256'].get(rel) == expected[name],
                'Write Intent source pin: ' + name)
    require(spec['run_id'] == plan['run_id'], 'run identity')
    require(spec['expected_rows'] == plan['expected_rows'], 'row pin')
    require(spec['expected_persons'] == plan['expected_persons'], 'Person pin')
    require(spec['expected_class_counts'] == plan['class_counts'], 'class pin')
    require(plan['mapper_sha256'] == expected['map_encounter_to_visit_candidate.py'],
            'mapper SHA not F2 approved')
    require(plan['contract_sha256'] == expected['visit-candidate-v1.json'],
            'candidate contract SHA not F2 approved')
    require(plan['mapping_contract_sha256'] == expected['visit-class-v1.json'],
            'mapping contract SHA not F2 approved')
    ctx = f2['raw_context']
    require(plan['raw_publish_run_id'] == ctx['raw_publish_run_id'],
            'Raw run pin')
    require(plan['expected_rows'] == ctx['expected_rows'], 'Raw row pin')
    require(spec['expected_persons'] == f2['expected_persons'], 'F2 Person pin')
    require(spec['expected_class_counts'] == f2['expected_class_counts'],
            'F2 class pin')
    require(spec['person_map_fingerprint'] == permit.get('person_map_fingerprint'),
            'Person map fingerprint permit pin')
    fingerprint = spec['person_map_fingerprint']
    require(isinstance(fingerprint, str) and len(fingerprint) == 64
            and all(c in '0123456789abcdef' for c in fingerprint),
            'invalid Person map fingerprint')
    return spec, plan, permit, json.loads(reservation_bytes), (
        plan_bytes, intent_bytes, reservation_bytes, listing_bytes)


def verify_live_lock_payload(live, requested, permit):
    """Compare K8s API server response; caller must fetch it live."""
    metadata = live.get('metadata', {})
    req_meta = requested['metadata']
    require(live.get('kind') == 'ConfigMap', 'not a ConfigMap')
    require(live.get('immutable') is True, 'live reservation mutable')
    require(metadata.get('name') == req_meta['name'], 'live lock name')
    require(metadata.get('namespace') == 'dw-spark', 'live lock namespace')
    require(metadata.get('uid') == permit['reservation_uid'], 'live UID drift')
    require(str(metadata.get('resourceVersion')) ==
            permit['reservation_resource_version'], 'live resourceVersion drift')
    require(live.get('data') == requested['data'], 'live reservation changed')
    require(metadata.get('labels') == req_meta['labels'], 'live lock labels drift')
    return True


def verify_live_lock(requested, permit):
    """Get exact ConfigMap from Kubernetes in-cluster HTTPS API, fail closed."""
    token = Path('/var/run/secrets/kubernetes.io/serviceaccount/token')
    ca = Path('/var/run/secrets/kubernetes.io/serviceaccount/ca.crt')
    require(token.is_file() and ca.is_file(), 'in-cluster K8s identity unavailable')
    require(os.environ.get('KUBERNETES_SERVICE_HOST'), 'missing K8s API host')
    host = os.environ['KUBERNETES_SERVICE_HOST']
    port = os.environ.get('KUBERNETES_SERVICE_PORT_HTTPS', '443')
    require(port.isdigit(), 'invalid Kubernetes API port')
    name = requested['metadata']['name']
    require(name.startswith('visit-proc-lock-') and len(name) <= 63,
            'unexpected lock name')
    url = ('https://' + host + ':' + port
           + '/api/v1/namespaces/dw-spark/configmaps/' + quote(name, safe=''))
    req = Request(url, headers={'Authorization': 'Bearer ' + token.read_text().strip(),
                                'Accept': 'application/json'}, method='GET')
    try:
        context = ssl.create_default_context(cafile=str(ca))
        with urlopen(req, context=context, timeout=12) as response:
            require(response.status == 200, 'K8s lock GET non-200')
            body = response.read(1024 * 1024 + 1)
            require(len(body) <= 1024 * 1024, 'oversized K8s lock response')
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise ValueError('PROCESSED_DRIVER_GUARD: K8s live lock unavailable') from exc
    verify_live_lock_payload(json.loads(body), requested, permit)
    return True


def verify_schema(fields, contract_fields):
    expected = [(f['name'], TYPE_NAMES[f['type']]) for f in contract_fields]
    require(fields == expected, 'Candidate schema/order mismatch')
    require('visit_occurrence_id' not in dict(fields), 'premature Visit ID')
    return expected


def main():
    from pyspark.sql import SparkSession, functions as F
    from canonical_gate import validate_contract, validate_metadata, validate_unique_key
    from verify_encounter_remote_metadata import verify_metadata
    from map_encounter_to_visit_candidate import map_encounter_to_candidate
    from visit_candidate_rules import validate_rules

    directory = Path(__file__).resolve().parent
    spec, plan, permit, reservation, blobs = verify_bundle(directory)
    plan_bytes, intent_bytes, reservation_bytes, listing_bytes = blobs
    f2 = spec['f2_input']
    ctx = f2['raw_context']
    require(ctx.get('status') == 'PASS', 'Raw not approved')
    require(os.environ.get('PGDATABASE') == 'omop', 'wrong PostgreSQL database')
    for key in ('PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD'):
        require(bool(os.environ.get(key)), 'missing PostgreSQL setting ' + key)
    raw_contract = json.loads((directory / 'encounter-v1.json').read_bytes())
    mapping = json.loads((directory / 'visit-class-v1.json').read_bytes())
    candidate_contract = json.loads((directory / 'visit-candidate-v1.json').read_bytes())
    class_mapping = validate_rules(mapping, raw_contract, candidate_contract)

    # Check live K8s lock BEFORE expensive Spark bootstrap as well as before write.
    verify_live_lock(reservation, permit)
    spark = (SparkSession.builder.appName('visit-processed-single-write')
             .config('spark.sql.session.timeZone', 'UTC').getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    try:
        def remote_bytes(uri):
            rows = (spark.read.format('binaryFile')
                    .load(uri.replace('s3://', 's3a://', 1))
                    .select('content').collect())
            require(len(rows) == 1, 'remote metadata object count')
            return bytes(rows[0]['content'])

        verify_metadata(ctx, remote_bytes(ctx['raw_manifest_uri']),
                        remote_bytes(ctx['dq_uri']))
        manifest = json.loads(remote_bytes(ctx['raw_manifest_uri']))
        raw = spark.read.parquet(ctx['raw_data_uri'].replace('s3://', 's3a://', 1)).cache()
        validate_contract(raw, raw_contract)
        keys = validate_unique_key(raw, raw_contract['primary_key'])
        require(keys['rows'] == plan['expected_rows'] and
                keys['unique_keys'] == keys['rows'], 'Raw row/unique key drift')
        validate_metadata(raw, dict(
            source_system=ctx['source'], source_version=ctx['source_version'],
            source_batch_id=ctx['batch_id'], source_ingest_date=ctx['ingest_date'],
            processing_run_id=ctx['processing_run_id'],
            source_file=manifest['source_file'],
            source_file_sha256=manifest['source_file_sha256'],
            source_file_size_bytes=manifest['source_file_size_bytes'],
            adapter_name='synthea_encounter_adapter', adapter_version='v1',
            canonical_version='v1',
        ))
        require(not raw.filter(F.col('end_datetime') < F.col('start_datetime'))
                .limit(1).count(), 'Raw Encounter dates reversed')

        def jdbc_read(sql):
            return (spark.read.format('jdbc')
                    .option('url', 'jdbc:postgresql://' + os.environ['PGHOST'] + ':'
                            + os.environ['PGPORT'] + '/omop')
                    .option('user', os.environ['PGUSER'])
                    .option('password', os.environ['PGPASSWORD'])
                    .option('driver', 'org.postgresql.Driver')
                    .option('sessionInitStatement',
                            'SET default_transaction_read_only = on')
                    .option('dbtable', '(' + sql + ') as proc_writer_ro')
                    .load())

        persons = jdbc_read('''
          SELECT m.source_system, m.source_person_id, m.person_id,
                 p.person_id AS cdm_person_id
          FROM etl.person_id_map m
          LEFT JOIN cdm.person p ON p.person_id = m.person_id
          WHERE m.source_system = 'synthea'
        ''').cache()
        require(not persons.filter(
            F.col('person_id').isNull() | F.col('cdm_person_id').isNull()
            | (F.col('person_id') <= 0)).limit(1).count(),
            'Person mapping/CDM FK invalid')
        require(not persons.groupBy('source_system', 'source_person_id')
                .count().filter(F.col('count') != 1).limit(1).count(),
                'Person map duplicate identity')
        fp = person_snapshot_fingerprint([
            (r['source_system'], r['source_person_id'], int(r['person_id']))
            for r in persons.select('source_system', 'source_person_id', 'person_id')
            .collect()
        ])
        require(fp == spec['person_map_fingerprint'], 'Person map snapshot changed')

        candidate = map_encounter_to_candidate(raw, persons, mapping, ctx).cache()
        expected_schema = verify_schema(
            [(f.name, f.dataType.simpleString()) for f in candidate.schema.fields],
            candidate_contract['fields'],
        )
        mandatory = [f['name'] for f in candidate_contract['fields'] if not f['nullable']]
        require(not candidate.filter(reduce(
            lambda a, b: a | b, [F.col(name).isNull() for name in mandatory]
        )).limit(1).count(), 'Candidate required null')
        require(not candidate.filter(
            (F.col('person_id') <= 0) | (F.col('visit_concept_id') <= 0)
            | (F.col('visit_start_datetime') > F.col('visit_end_datetime'))
            | (F.col('visit_start_date') != F.to_date('visit_start_datetime'))
            | (F.col('visit_end_date') != F.to_date('visit_end_datetime'))
            | (F.col('visit_type_concept_id') != mapping['visit_type_concept_id'])
            | (F.col('visit_source_value') != F.col('encounter_class'))
        ).limit(1).count(), 'Candidate concept/date/type/source invalid')
        deferred = ('provider_id', 'care_site_id', 'visit_source_concept_id',
                    'admitted_from_concept_id', 'admitted_from_source_value',
                    'discharged_to_concept_id', 'discharged_to_source_value',
                    'preceding_visit_occurrence_id')
        for name in deferred:
            require(not candidate.filter(F.col(name).isNotNull()).limit(1).count(),
                    'unexpected populated deferred field: ' + name)
        grouped = candidate.groupBy('encounter_class', 'visit_concept_id').count().collect()
        class_counts = {}
        for record in grouped:
            klass, concept, n = record['encounter_class'], record['visit_concept_id'], record['count']
            require(klass in class_mapping and concept == class_mapping[klass],
                    'Visit mapping mismatch')
            class_counts[klass] = class_counts.get(klass, 0) + n
        require(class_counts == plan['class_counts'], 'class distribution drift')
        require(candidate.count() == plan['expected_rows'], 'Candidate count drift')
        require(candidate.select('source_system', 'source_encounter_id')
                .distinct().count() == plan['expected_rows'], 'Candidate keys duplicated')
        require(candidate.select('person_id').distinct().count()
                == plan['expected_persons'], 'referenced Person count drift')

        concepts = set(class_mapping.values()) | {mapping['visit_type_concept_id']}
        concept_rows = jdbc_read(
            'SELECT concept_id,domain_id,standard_concept,invalid_reason,'
            'valid_start_date,valid_end_date FROM cdm.concept WHERE concept_id IN ('
            + ','.join(map(str, sorted(concepts))) + ')'
        ).collect()
        require({r['concept_id'] for r in concept_rows} == concepts,
                'Visit vocabulary concept missing')
        today = datetime.now(timezone.utc).date()
        for row in concept_rows:
            domain = ('Type Concept' if row['concept_id'] == mapping['visit_type_concept_id']
                      else 'Visit')
            require(row['domain_id'] == domain and row['standard_concept'] == 'S'
                    and row['invalid_reason'] is None
                    and row['valid_start_date'] <= today <= row['valid_end_date'],
                    'Visit vocabulary concept invalid')

        verify_metadata(ctx, remote_bytes(ctx['raw_manifest_uri']),
                        remote_bytes(ctx['dq_uri']))
        verify_live_lock(reservation, permit)
        # The core re-checks permit and S3A prefix existence immediately before output.
        result = write_once_with_readback(
            candidate, spark, permit, plan_bytes, intent_bytes, reservation_bytes,
            listing_bytes, expected_schema, plan['expected_rows'],
            plan['expected_persons'], plan['class_counts'],
        )
        print('VISIT_PROCESSED_WRITE_RESULT=' +
              json.dumps(result, sort_keys=True), flush=True)
    finally:
        spark.stop()


if __name__ == '__main__':
    main()
