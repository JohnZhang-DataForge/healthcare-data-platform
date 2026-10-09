#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_PAGER=cat

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
STAGE=''

echo '#### TASK003 STEP05G2C2B WRITER CORE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"
  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2B WRITER CORE OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

for rel in \
  spark/contracts/omop/visit-candidate-v1.json \
  spark/contracts/processed/visit-writer-safety-v1.json \
  apps/task003/build_visit_writer_reservation.py \
  spark/apps/visit/map_encounter_to_visit_candidate.py
do
  [[ -s "$ROOT/$rel" && ! -L "$ROOT/$rel" ]] || {
    echo "ERROR: missing prerequisite $rel"
    exit 1
  }
done

STAGE=$(mktemp -d /data/spark/temp_shell/05g2c2b-stage.XXXXXXXX)

mkdir -p \
  "$STAGE/spark/apps/visit" \
  "$STAGE/tests/task003"

# ========================================================
# 1. Spark Writer core
# ========================================================

cat > "$STAGE/spark/apps/visit/processed_visit_writer_core.py" <<'PY_APP'
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
PY_APP

# ========================================================
# 2. Unit and negative tests
# ========================================================

cat > "$STAGE/tests/task003/test_processed_visit_writer_core.py" <<'PY_TEST'
import ast
import hashlib
import json
import sys
import unittest

from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'spark/apps/visit')
)

from processed_visit_writer_core import (
    validate_permit,
    person_snapshot_fingerprint,
    sha,
)


def encode(value):
    return (json.dumps(value, sort_keys=True) + '\n').encode()


class WriterCoreTests(unittest.TestCase):

    def setUp(self):
        self.plan = dict(
            status='PLANNED',
            run_id='visit-test',
            persisted=False,
            published=False,
            visit_ids_allocated=0,
            postgresql_write=False,
            base_uri=(
                's3://health-processed/'
                'contract_version=v1/'
                'entity=visit_occurrence/'
                'source=synthea/'
                'source_version=v3.3.0/'
                'ingest_date=2026-10-08/'
                'batch_id=test/'
                'raw_publish_run_id=raw-test/'
                'run_id=visit-test'
            ),
        )

        self.plan['data_uri'] = self.plan['base_uri'] + '/data/'
        self.plan_bytes = encode(self.plan)

        self.intent = dict(
            run_id='visit-test',
            plan_sha256=sha(self.plan_bytes),
            write_authorized=False,
        )
        self.intent_bytes = encode(self.intent)

        self.record = dict(
            write_intent_sha256=sha(self.intent_bytes),
            plan_sha256=sha(self.plan_bytes),
            run_id='visit-test',
            bucket='health-processed',
            prefix=(
                self.plan['base_uri']
                .split('health-processed/', 1)[1] + '/'
            ),
            write_authorized=False,
            mode='EXCLUSIVE_CREATE_ONLY',
        )

        self.request = dict(
            kind='ConfigMap',
            immutable=True,
            metadata={
                'name': 'visit-proc-lock-example',
                'namespace': 'dw-spark',
            },
            data={
                'reservation.json': json.dumps(self.record)
            },
        )
        self.request_bytes = encode(self.request)

        self.listing_bytes = encode({
            'RequestCharged': None
        })

        now = datetime(
            2026, 10, 9, 20, 0,
            tzinfo=timezone.utc,
        )
        self.now = now

        self.permit = dict(
            task='TASK-003',
            step='STEP-05G2C2C',
            status='AUTHORIZED_FOR_SINGLE_WRITE',
            write_authorized=True,
            reservation_created_by_k8s_create=True,
            reservation_verified=True,
            fresh_s3_relist_passed=True,
            fresh_prefix_classification='EMPTY',
            candidate_published=False,
            postgresql_write=False,
            run_id='visit-test',
            data_uri=self.plan['data_uri'],
            plan_sha256=sha(self.plan_bytes),
            intent_sha256=sha(self.intent_bytes),
            reservation_spec_sha256=sha(self.request_bytes),
            fresh_listing_sha256=sha(self.listing_bytes),
            reservation_name=self.request['metadata']['name'],
            reservation_uid='123e4567-e89b-12d3-a456-426614174000',
            reservation_resource_version='1234567',
            issued_at_utc=(
                now - timedelta(seconds=10)
            ).isoformat(),
            expires_at_utc=(
                now + timedelta(seconds=90)
            ).isoformat(),
        )

    def check(self):
        return validate_permit(
            self.permit,
            self.plan_bytes,
            self.intent_bytes,
            self.request_bytes,
            self.listing_bytes,
            self.now,
        )

    def test_valid_short_lived_permit(self):
        self.assertEqual(self.check(), self.plan)

    def test_absent_lock_denied(self):
        self.permit['reservation_verified'] = False
        with self.assertRaises(ValueError):
            self.check()

    def test_unapproved_listing_denied(self):
        self.permit['fresh_s3_relist_passed'] = False
        with self.assertRaises(ValueError):
            self.check()

    def test_listing_not_empty_denied(self):
        self.listing_bytes = encode({
            'Contents': [
                {'Key': 'foreign', 'Size': 2}
            ],
            'KeyCount': 1,
        })

        self.permit['fresh_listing_sha256'] = sha(
            self.listing_bytes
        )

        with self.assertRaises(ValueError):
            self.check()

    def test_expired_denied(self):
        self.permit['expires_at_utc'] = (
            self.now - timedelta(seconds=1)
        ).isoformat()

        with self.assertRaises(ValueError):
            self.check()

    def test_excessive_lifetime_denied(self):
        self.permit['expires_at_utc'] = (
            self.now + timedelta(seconds=400)
        ).isoformat()

        with self.assertRaises(ValueError):
            self.check()

    def test_plan_drift_denied(self):
        self.plan['run_id'] = 'different'
        self.plan_bytes = encode(self.plan)

        with self.assertRaises(ValueError):
            self.check()

    def test_intent_drift_denied(self):
        self.intent['run_id'] = 'different'
        self.intent_bytes = encode(self.intent)

        with self.assertRaises(ValueError):
            self.check()

    def test_reservation_drift_denied(self):
        self.request['metadata']['name'] = 'different'
        self.request_bytes = encode(self.request)

        with self.assertRaises(ValueError):
            self.check()

    def test_valid_person_fingerprint_is_order_independent(self):
        people = [
            ('synthea', 'a', 1),
            ('synthea', 'b', 2),
        ]

        self.assertEqual(
            person_snapshot_fingerprint(people),
            person_snapshot_fingerprint(
                list(reversed(people))
            ),
        )

    def test_duplicate_person_denied(self):
        with self.assertRaises(ValueError):
            person_snapshot_fingerprint([
                ('synthea', 'a', 1),
                ('synthea', 'a', 2),
            ])

    def test_no_automatic_spark_or_s3_actions_on_import(self):
        path = (
            ROOT /
            'spark/apps/visit/processed_visit_writer_core.py'
        )
        source = path.read_text()
        tree = ast.parse(source)

        self.assertFalse(
            any(
                isinstance(n, ast.Call)
                for n in tree.body
            )
        )
        self.assertNotIn(
            "mode('overwrite')",
            source,
        )


if __name__ == '__main__':
    unittest.main()
PY_TEST

# ========================================================
# 3. Local source and unit tests
# ========================================================

echo '=== 1. Parse source and run unit tests ==='

python3 - "$STAGE" <<'PY_CHECK'
import ast
import sys
from pathlib import Path

stage = Path(sys.argv[1])

for rel in (
    'spark/apps/visit/processed_visit_writer_core.py',
    'tests/task003/test_processed_visit_writer_core.py',
):
    ast.parse(
        (stage / rel).read_text(),
        filename=rel,
    )

print('SOURCE_AST=PASS')
PY_CHECK

PYTHONPATH="$STAGE/spark/apps/visit" \
python3 -m unittest discover \
    -s "$STAGE/tests/task003" \
    -p 'test_processed_visit_writer_core.py' -v

# ========================================================
# 4. Writer boundary checks
# ========================================================

echo '=== 2. Verify write boundary ==='

python3 - "$STAGE" <<'PY_BOUNDARY'
import ast
import sys
from pathlib import Path

src = (
    Path(sys.argv[1])
    / 'spark/apps/visit/processed_visit_writer_core.py'
).read_text()

tree = ast.parse(src)

functions = {
    n.name
    for n in tree.body
    if isinstance(n, ast.FunctionDef)
}

required = {
    'validate_permit',
    'person_snapshot_fingerprint',
    'write_once_with_readback',
}

assert required.issubset(functions)
assert "candidate.write.mode('errorifexists').parquet(uri)" in src
assert 'exceptAll' in src

assert not any(
    isinstance(n, ast.If)
    and isinstance(n.test, ast.Compare)
    and isinstance(n.test.left, ast.Name)
    and n.test.left.id == '__name__'
    for n in tree.body
)

print('WRITER_BOUNDARY_STATIC_CHECK=PASS')
PY_BOUNDARY

# ========================================================
# 5. Conflict check and canonical installation
# ========================================================

FILES=(
    spark/apps/visit/processed_visit_writer_core.py
    tests/task003/test_processed_visit_writer_core.py
)

GEN=scripts/task003/05g2c2b-prepare-visit-processed-writer-core.sh

for rel in "${FILES[@]}"; do
    if [[ -L "$ROOT/$rel" ]] || {
        [[ -e "$ROOT/$rel" ]] &&
        ! cmp -s "$STAGE/$rel" "$ROOT/$rel"
    }; then
        echo "ERROR: canonical source conflict: $rel"
        exit 1
    fi
done

if [[ -L "$ROOT/$GEN" ]] || {
    [[ -e "$ROOT/$GEN" ]] &&
    ! cmp -s "${BASH_SOURCE[0]}" "$ROOT/$GEN"
}; then
    echo "ERROR: canonical generator conflict: $GEN"
    exit 1
fi

echo '=== 3. Install canonical files ==='

for rel in "${FILES[@]}"; do
    mkdir -p "$(dirname "$ROOT/$rel")"
    install -m 644 "$STAGE/$rel" "$ROOT/$rel"
    echo "CANONICAL_SOURCE_READY=$rel"
done

mkdir -p "$ROOT/scripts/task003"

if [[ "${BASH_SOURCE[0]}" -ef "$ROOT/$GEN" ]]; then
    echo "CANONICAL_GENERATOR_REUSED=$GEN"
else
    install -m 755 "${BASH_SOURCE[0]}" "$ROOT/$GEN"
    echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo 'STEP05G2C2B_WRITER_CORE_SOURCE=PASS'
echo 'RESERVATION_ACQUIRED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
echo 'GIT_COMMIT=NO'
