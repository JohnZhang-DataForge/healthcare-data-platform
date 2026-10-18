"""STEP05G2C2B: reusable guarded Spark Parquet writer.

Only a later orchestrator can obtain a Kubernetes CREATE
reservation, re-list SeaweedFS, build a short-lived permit
and invoke this module.

A permit is a consistency check, not a cryptographic
or S3-native lock.
"""

import hashlib
import json
from datetime import datetime, timezone
from urllib.parse import urlsplit


def require(condition, message):
    if not condition:
        raise ValueError('WRITER_GUARD: ' + message)


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def _time(value):
    require(isinstance(value, str), 'invalid permit timestamp')
    try:
        result = datetime.fromisoformat(
            value.replace('Z', '+00:00')
        )
    except ValueError as exc:
        raise ValueError('WRITER_GUARD: bad timestamp') from exc

    require(result.tzinfo is not None, 'timezone required')
    return result.astimezone(timezone.utc)


def validate_permit(
    permit,
    plan_bytes,
    intent_bytes,
    reservation_bytes,
    listing_bytes,
    now=None,
):
    """Check a pinned short-lived permit.

    Does NOT independently verify that a live Kubernetes
    lock is still present. The orchestrator must perform
    that check against the Kubernetes API.
    """

    plan = json.loads(plan_bytes)
    intent = json.loads(intent_bytes)
    request = json.loads(reservation_bytes)
    listing = json.loads(listing_bytes)

    now = now or datetime.now(timezone.utc)
    require(now.tzinfo is not None, 'clock missing timezone')
    now = now.astimezone(timezone.utc)

    exact = {
        'task': 'TASK-003',
        'step': 'STEP-05G2C2C',
        'status': 'AUTHORIZED_FOR_SINGLE_WRITE',
        'write_authorized': True,
        'reservation_created_by_k8s_create': True,
        'reservation_verified': True,
        'fresh_s3_relist_passed': True,
        'fresh_prefix_classification': 'EMPTY',
        'candidate_published': False,
        'postgresql_write': False,
    }

    for key, expected in exact.items():
        require(
            type(permit.get(key)) is type(expected)
            and permit[key] == expected,
            'permit ' + key,
        )

    pins = {
        'run_id': plan['run_id'],
        'data_uri': plan['data_uri'],
        'plan_sha256': sha(plan_bytes),
        'intent_sha256': sha(intent_bytes),
        'reservation_spec_sha256': sha(reservation_bytes),
        'fresh_listing_sha256': sha(listing_bytes),
        'reservation_name': request['metadata']['name'],
    }

    for key, value in pins.items():
        require(
            permit.get(key) == value,
            'permit pin ' + key,
        )

    require(
        intent.get('plan_sha256') == sha(plan_bytes),
        'intent plan pin',
    )
    require(
        intent.get('run_id') == plan['run_id'],
        'intent run identity',
    )
    require(
        intent.get('write_authorized') is False,
        'intent prematurely approved',
    )

    require(
        request.get('kind') == 'ConfigMap'
        and request.get('immutable') is True,
        'reservation resource',
    )
    require(
        request.get('metadata', {}).get('namespace') == 'dw-spark',
        'reservation namespace',
    )

    record = json.loads(request['data']['reservation.json'])

    require(
        record.get('write_intent_sha256') == sha(intent_bytes),
        'reservation intent pin',
    )
    require(
        record.get('run_id') == plan['run_id'],
        'reservation run pin',
    )
    require(
        record.get('plan_sha256') == sha(plan_bytes),
        'reservation plan pin',
    )
    require(
        record.get('write_authorized') is False,
        'reservation incorrectly claims approval',
    )
    require(
        record.get('mode') == 'EXCLUSIVE_CREATE_ONLY',
        'reservation mode',
    )

    require(
        isinstance(permit.get('reservation_uid'), str)
        and len(permit['reservation_uid']) >= 8,
        'missing Kubernetes UID',
    )
    require(
        isinstance(permit.get('reservation_resource_version'), str)
        and permit['reservation_resource_version'].isdigit(),
        'missing Kubernetes resourceVersion',
    )

    issued = _time(permit.get('issued_at_utc'))
    expires = _time(permit.get('expires_at_utc'))

    require(
        issued <= now <= expires,
        'permit expired or not yet valid',
    )

    duration = (expires - issued).total_seconds()
    require(
        0 < duration <= 300,
        'permit lifetime must be <=300 seconds',
    )

    parsed = urlsplit(plan['base_uri'])

    require(
        parsed.scheme == 's3'
        and parsed.netloc == 'health-processed'
        and not parsed.query
        and not parsed.fragment,
        'unexpected output bucket',
    )

    require(
        record.get('bucket') == 'health-processed'
        and record.get('prefix') == parsed.path.lstrip('/') + '/',
        'reservation S3 prefix pin',
    )

    require(
        plan['data_uri'] == plan['base_uri'] + '/data/',
        'unexpected output URI',
    )

    require(
        plan['published'] is False
        and plan['persisted'] is False,
        'plan incorrectly claims publication',
    )

    require(
        plan['visit_ids_allocated'] == 0
        and plan['postgresql_write'] is False,
        'early database write',
    )

    # SeaweedFS may return {"RequestCharged": null}
    # for a valid empty listing.
    require(
        isinstance(listing, dict)
        and any(
            k in listing
            for k in ('Contents', 'KeyCount', 'RequestCharged')
        ),
        'malformed S3 listing',
    )

    require(
        listing.get('IsTruncated', False) is False
        and not listing.get('NextContinuationToken'),
        'truncated S3 listing',
    )

    require(
        listing.get('Contents', []) == [],
        'nonempty S3 listing',
    )

    if 'KeyCount' in listing:
        require(
            type(listing['KeyCount']) is int
            and listing['KeyCount'] == 0,
            'contradictory KeyCount',
        )

    return plan


def person_snapshot_fingerprint(records):
    """Stable hash of read-only Synthea Person ID Map."""

    normalized = []
    identities = set()

    for source_system, source_person_id, person_id in records:
        require(
            source_system == 'synthea',
            'unknown Person source',
        )
        require(
            isinstance(source_person_id, str)
            and bool(source_person_id),
            'blank source Person ID',
        )
        require(
            type(person_id) is int and person_id > 0,
            'bad OMOP Person ID',
        )

        key = (source_system, source_person_id)

        require(
            key not in identities,
            'duplicate Person identity',
        )

        identities.add(key)
        normalized.append(
            [source_system, source_person_id, person_id]
        )

    require(bool(normalized), 'empty Person map')

    blob = json.dumps(
        sorted(normalized),
        separators=(',', ':'),
        ensure_ascii=False,
    ).encode('utf-8')

    return sha(blob)


def write_once_with_readback(
    candidate,
    spark,
    permit,
    plan_bytes,
    intent_bytes,
    reservation_bytes,
    listing_bytes,
    expected_schema,
    expected_rows,
    expected_persons,
    class_counts,
):
    """Write an authorized Candidate once and verify readback.

    Caller must confirm the real Kubernetes reservation,
    its UID, the fresh S3 listing and upstream data quality.

    Failed/partial writes must not be automatically retried.
    """

    plan = validate_permit(
        permit,
        plan_bytes,
        intent_bytes,
        reservation_bytes,
        listing_bytes,
    )

    require(
        plan['status'] == 'PLANNED'
        and plan['published'] is False,
        'unexpected plan state',
    )

    require(
        type(expected_rows) is int and expected_rows > 0,
        'invalid planned row count',
    )
    require(
        type(expected_persons) is int and expected_persons > 0,
        'invalid planned Person count',
    )
    require(
        plan['expected_rows'] == expected_rows
        and plan['expected_persons'] == expected_persons,
        'planned counts mismatch',
    )
    require(
        plan['class_counts'] == class_counts,
        'planned class counts mismatch',
    )

    uri = plan['data_uri'].replace('s3://', 's3a://', 1)
    base = plan['base_uri'].replace('s3://', 's3a://', 1)

    require(
        uri.startswith('s3a://health-processed/')
        and uri.endswith('/data/'),
        'wrong write destination',
    )

    actual_schema = [
        (field.name, field.dataType.simpleString())
        for field in candidate.schema.fields
    ]

    require(
        actual_schema == expected_schema,
        'candidate schema mismatch',
    )
    require(
        'visit_occurrence_id' not in dict(actual_schema),
        'premature Visit ID',
    )
    require(
        candidate.count() == expected_rows,
        'candidate row drift',
    )
    require(
        candidate.select('person_id').distinct().count()
        == expected_persons,
        'referenced Person drift',
    )
    require(
        candidate.select(
            'source_system', 'source_encounter_id'
        ).distinct().count() == expected_rows,
        'duplicate candidate key',
    )

    # Secondary S3A guard immediately before writing.
    jvm = spark.sparkContext._jvm
    hconf = spark.sparkContext._jsc.hadoopConfiguration()
    path = jvm.org.apache.hadoop.fs.Path(base)
    fs = path.getFileSystem(hconf)

    require(
        not fs.exists(path),
        'processed run prefix already exists',
    )

    # Never use overwrite. This creates data only, not DQ or Manifest.
    candidate.write.mode('errorifexists').parquet(uri)

    persisted = spark.read.parquet(uri)

    readback_schema = [
        (field.name, field.dataType.simpleString())
        for field in persisted.schema.fields
    ]

    require(
        readback_schema == expected_schema,
        'readback schema drift',
    )
    require(
        persisted.count() == expected_rows,
        'readback row drift',
    )
    require(
        persisted.select(
            'source_system', 'source_encounter_id'
        ).distinct().count() == expected_rows,
        'readback duplicate key',
    )
    require(
        persisted.select('person_id').distinct().count()
        == expected_persons,
        'readback Person drift',
    )

    # Compare data as multisets; Parquet row order is not guaranteed.
    require(
        not candidate.exceptAll(persisted).limit(1).count(),
        'write lost/changed candidate rows',
    )
    require(
        not persisted.exceptAll(candidate).limit(1).count(),
        'write introduced/changed candidate rows',
    )

    counts = {
        r['encounter_class']: r['count']
        for r in (
            persisted.groupBy('encounter_class')
            .count()
            .collect()
        )
    }

    require(
        counts == class_counts,
        'readback class count drift',
    )

    return {
        'status': 'DATA_READBACK_PASS',
        'rows': expected_rows,
        'unique_keys': expected_rows,
        'referenced_persons': expected_persons,
        'class_counts': counts,
        'data_uri': plan['data_uri'],
        'write_mode': 'errorifexists',
        'dq_published': False,
        'manifest_published': False,
        'cdm_write': False,
    }
