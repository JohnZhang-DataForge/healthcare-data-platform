#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
SOURCE="${BASH_SOURCE[0]:-}"
STAGE=''

echo '#### TASK003 STEP05G2C2C2B2 RUNTIME BUNDLE SOURCE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"

  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C2B2 RUNTIME BUNDLE SOURCE OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ -n "$SOURCE" && -f "$SOURCE" ]] || {
  echo 'ERROR: execute saved installer with bash'
  exit 2
}

for rel in \
  apps/task003/plan_visit_processed.py \
  apps/task003/prepare_visit_writer_bundle_inventory.py \
  spark/apps/visit/processed_visit_writer_core.py \
  spark/apps/visit/run_visit_processed_writer.py \
  spark/manifests/task003/visit-candidate-preflight.yaml.tpl
do
  [[ -s "$ROOT/$rel" && ! -L "$ROOT/$rel" ]] || {
    echo "ERROR: missing prerequisite $rel"
    exit 2
  }
done

STAGE=$(mktemp -d /data/spark/temp_shell/g2c2c2b2.XXXXXXXX)

mkdir -p \
  "$STAGE/apps/task003" \
  "$STAGE/tests/task003" \
  "$STAGE/scripts/task003" \
  "$STAGE/spark/manifests/task003" \
  "$STAGE/spark/apps/visit"

# ========================================================
# 1. SparkApplication template
# ========================================================

cat > "$STAGE/spark/manifests/task003/visit-processed-writer.yaml.tpl" <<'YAML'
apiVersion: sparkoperator.k8s.io/v1beta2
kind: SparkApplication

metadata:
  name: __APP_NAME__
  namespace: dw-spark

  labels:
    healthcare-task: task003
    healthcare-domain: visit
    healthcare-step: processed-write

spec:
  type: Python
  mode: cluster

  image: spark:3.5.7-python3
  imagePullPolicy: IfNotPresent

  mainApplicationFile: local:///opt/spark/app/run_visit_processed_writer.py

  sparkVersion: "3.5.7"

  restartPolicy:
    type: Never

  deps:
    jars:
      - https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar
      - https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar
      - https://repo1.maven.org/maven2/org/wildfly/openssl/wildfly-openssl/1.0.7.Final/wildfly-openssl-1.0.7.Final.jar
      - https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.4/postgresql-42.7.4.jar

  sparkConf:
    spark.hadoop.fs.s3a.endpoint: http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333
    spark.hadoop.fs.s3a.path.style.access: "true"
    spark.hadoop.fs.s3a.connection.ssl.enabled: "false"
    spark.hadoop.fs.s3a.endpoint.region: us-east-1
    spark.hadoop.fs.s3a.aws.credentials.provider: com.amazonaws.auth.EnvironmentVariableCredentialsProvider

    spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version: "2"

    spark.kubernetes.driver.ownPersistentVolumeClaim: "false"
    spark.kubernetes.driver.reusePersistentVolumeClaim: "false"

  driver:
    cores: 1
    coreLimit: "1"
    memory: 1g

    serviceAccount: spark-job

    nodeSelector:
      workload: platform

    envFrom:
      - secretRef:
          name: dw-spark-s3-secret

      - secretRef:
          name: dw-spark-omop-secret

    volumeMounts:
      - name: spark-app
        mountPath: /opt/spark/app
        readOnly: true

  executor:
    instances: 1
    cores: 1
    coreLimit: "1"
    memory: 1g

    nodeSelector:
      workload: platform

    envFrom:
      - secretRef:
          name: dw-spark-s3-secret

      - secretRef:
          name: dw-spark-omop-secret

    volumeMounts:
      - name: spark-app
        mountPath: /opt/spark/app
        readOnly: true

  volumes:
    - name: spark-app
      configMap:
        name: __CONFIGMAP_NAME__
YAML

# ========================================================
# 2. Runtime Bundle builder
# ========================================================

cat > "$STAGE/apps/task003/build_visit_processed_runtime_bundle.py" <<'PY_APP'
"""Build immutable Visit Processed runtime manifests.

This program does NOT call Kubernetes, Spark, S3 or PostgreSQL.

A later execution step must first:
- create the exclusive Reservation ConfigMap;
- verify its live UID/resourceVersion;
- obtain a fresh EMPTY S3 listing;
- generate a short-lived write permit.

Only then can this builder package the exact source/evidence snapshot
into an immutable runtime ConfigMap manifest and SparkApplication YAML.
"""

import argparse
import hashlib
import json
import re
import sys

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'spark/apps/visit')
)

sys.path.insert(
    0,
    str(ROOT / 'apps/task003')
)

from plan_visit_processed import save_once
from processed_visit_writer_core import validate_permit


SOURCE_PATHS = {
    'map_encounter_to_visit_candidate.py':
        'spark/apps/visit/map_encounter_to_visit_candidate.py',

    'validate_visit_candidate_preflight.py':
        'spark/apps/visit/validate_visit_candidate_preflight.py',

    'canonical_gate.py':
        'spark/common/canonical_gate.py',

    'visit_candidate_rules.py':
        'apps/task003/visit_candidate_rules.py',

    'verify_encounter_remote_metadata.py':
        'apps/task003/verify_encounter_remote_metadata.py',

    'resolve_approved_encounter_raw.py':
        'apps/task003/resolve_approved_encounter_raw.py',

    'encounter-v1.json':
        'spark/contracts/canonical/encounter-v1.json',

    'visit-class-v1.json':
        'spark/contracts/omop/visit-class-v1.json',

    'visit-candidate-v1.json':
        'spark/contracts/omop/visit-candidate-v1.json',

    'run_visit_processed_writer.py':
        'spark/apps/visit/run_visit_processed_writer.py',

    'processed_visit_writer_core.py':
        'spark/apps/visit/processed_visit_writer_core.py',
}


STATIC_ARTIFACTS = {
    'step05f2-run-state.json': 'f2',
    'processed-plan.json': 'plan',
    'processed-write-intent.json': 'intent',
    'reservation-create.json': 'reservation',
}


FUTURE_ARTIFACTS = (
    'fresh-s3-listing.json',
    'write-permit.json',
)


DNS_NAME = re.compile(
    r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
)


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(
            'RUNTIME_BUNDLE_CONFLICT: ' + message
        )


def decode_text(blob, label):
    require(
        b'\x00' not in blob,
        label + ' contains NUL'
    )

    try:
        return blob.decode('utf-8')

    except UnicodeDecodeError as exc:
        raise ValueError(
            'RUNTIME_BUNDLE_CONFLICT: non-UTF8 ' + label
        ) from exc


def safe_kubernetes_name(name):
    require(
        isinstance(name, str)
        and len(name) <= 63
        and DNS_NAME.fullmatch(name),
        'unsafe Kubernetes name'
    )

    return name


def validate_template(template_bytes):
    template = decode_text(
        template_bytes,
        'SparkApplication template'
    )

    require(
        template.count('__APP_NAME__') == 1,
        'app placeholder'
    )

    require(
        template.count('__CONFIGMAP_NAME__') == 1,
        'ConfigMap placeholder'
    )

    without_known = (
        template
        .replace('__APP_NAME__', '')
        .replace('__CONFIGMAP_NAME__', '')
    )

    require(
        '__' not in without_known,
        'unknown template placeholder'
    )

    required = (
        'apiVersion: sparkoperator.k8s.io/v1beta2',
        'kind: SparkApplication',
        'namespace: dw-spark',
        'image: spark:3.5.7-python3',
        (
            'mainApplicationFile: '
            'local:///opt/spark/app/'
            'run_visit_processed_writer.py'
        ),
        'sparkVersion: "3.5.7"',
        'serviceAccount: spark-job',
        'name: dw-spark-s3-secret',
        'name: dw-spark-omop-secret',
        'workload: platform',
        (
            'spark.hadoop.fs.s3a.endpoint: '
            'http://dw-seaweedfs-s3.'
            'dw-seaweedfs.svc.cluster.local:8333'
        ),
        'spark.hadoop.fs.s3a.path.style.access: "true"',
        (
            'spark.hadoop.mapreduce.'
            'fileoutputcommitter.algorithm.version: "2"'
        ),
    )

    for item in required:
        require(
            item in template,
            'template missing: ' + item
        )

    require(
        'restartPolicy:\n    type: Never' in template,
        'restart policy'
    )

    return template


def build_bundle(
    run_id,
    inventory_bytes,
    f2_bytes,
    plan_bytes,
    intent_bytes,
    reservation_bytes,
    listing_bytes,
    permit_bytes,
    source_bytes,
    template_bytes,
    now=None,
):
    inventory = json.loads(inventory_bytes)
    f2 = json.loads(f2_bytes)
    plan = json.loads(plan_bytes)
    intent = json.loads(intent_bytes)
    reservation = json.loads(reservation_bytes)
    permit = json.loads(permit_bytes)

    # Validate JSON before handing bytes to the Writer Core.
    json.loads(listing_bytes)

    require(
        inventory.get('schema')
        == 'task003.visit_processed.bundle_inventory.v1',
        'inventory schema'
    )

    require(
        inventory.get('status')
        == 'SOURCE_INVENTORY_ONLY',
        'inventory status'
    )

    require(
        inventory.get('run_id') == run_id,
        'inventory run'
    )

    require(
        plan.get('run_id')
        == intent.get('run_id')
        == run_id,
        'run identity'
    )

    require(
        inventory.get('reservation_name')
        == reservation['metadata']['name'],
        'inventory reservation name'
    )

    require(
        inventory.get('future_artifacts_required')
        == list(FUTURE_ARTIFACTS),
        'future artifact inventory'
    )

    # This verifies:
    # - live lock fields recorded in permit;
    # - plan / intent / reservation hashes;
    # - fresh S3 listing hash;
    # - listing EMPTY state;
    # - short permit lifetime.
    validate_permit(
        permit,
        plan_bytes,
        intent_bytes,
        reservation_bytes,
        listing_bytes,
        now=now or datetime.now(timezone.utc),
    )

    fingerprint = permit.get(
        'person_map_fingerprint'
    )

    require(
        isinstance(fingerprint, str)
        and len(fingerprint) == 64
        and all(
            char in '0123456789abcdef'
            for char in fingerprint
        ),
        'Person map fingerprint'
    )

    require(
        f2.get('task') == 'TASK-003'
        and f2.get('step') == 'STEP-05F2'
        and f2.get('status') == 'PASS',
        'F2 evidence'
    )

    require(
        plan.get('source_f2_evidence_sha256')
        == sha(f2_bytes),
        'plan F2 pin'
    )

    require(
        intent.get('step05f2_sha256')
        == sha(f2_bytes),
        'intent F2 pin'
    )

    require(
        intent.get('plan_sha256')
        == sha(plan_bytes),
        'intent plan pin'
    )

    require(
        plan.get('expected_rows')
        == f2['result']['candidate_rows'],
        'row pin'
    )

    require(
        plan.get('expected_persons')
        == f2['result']['referenced_persons'],
        'Person pin'
    )

    require(
        set(source_bytes)
        == set(SOURCE_PATHS),
        'source inventory'
    )

    inventory_sources = inventory.get(
        'source_files',
        {}
    )

    require(
        set(inventory_sources)
        == set(SOURCE_PATHS),
        'inventory source catalog'
    )

    for name, repo_path in SOURCE_PATHS.items():
        record = inventory_sources[name]

        require(
            record['repo_path'] == repo_path,
            'repo path ' + name
        )

        require(
            record['sha256']
            == sha(source_bytes[name]),
            'source SHA ' + name
        )

        require(
            record['size_bytes']
            == len(source_bytes[name]),
            'source size ' + name
        )

    static_blobs = {
        'f2': f2_bytes,
        'plan': plan_bytes,
        'intent': intent_bytes,
        'reservation': reservation_bytes,
    }

    inventory_artifacts = inventory.get(
        'static_artifacts',
        {}
    )

    require(
        set(inventory_artifacts)
        == set(STATIC_ARTIFACTS),
        'static artifact catalog'
    )

    for filename, key in STATIC_ARTIFACTS.items():
        record = inventory_artifacts[filename]

        require(
            record['sha256']
            == sha(static_blobs[key]),
            'artifact SHA ' + filename
        )

        require(
            record['size_bytes']
            == len(static_blobs[key]),
            'artifact size ' + filename
        )

    template = validate_template(
        template_bytes
    )

    artifact_bytes = {
        'step05f2-run-state.json':
            f2_bytes,

        'processed-plan.json':
            plan_bytes,

        'processed-write-intent.json':
            intent_bytes,

        'reservation-create.json':
            reservation_bytes,

        'fresh-s3-listing.json':
            listing_bytes,

        'write-permit.json':
            permit_bytes,
    }

    artifact_sha256 = {
        name: sha(blob)
        for name, blob
        in artifact_bytes.items()
    }

    driver_input = {
        'schema':
            'task003.visit_processed.spark_driver.v1',

        'task':
            'TASK-003',

        'step':
            'STEP-05G2C2C',

        'run_id':
            run_id,

        'source_file_sha256':
            f2['input']['mounted_file_sha256'],

        'artifact_sha256':
            artifact_sha256,

        'f2_input':
            f2['input'],

        'expected_rows':
            plan['expected_rows'],

        'expected_persons':
            plan['expected_persons'],

        'expected_class_counts':
            plan['class_counts'],

        'person_map_fingerprint':
            fingerprint,
    }

    driver_input_bytes = (
        json.dumps(
            driver_input,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + '\n'
    ).encode('utf-8')

    configmap_data = {
        name: decode_text(blob, name)
        for name, blob in source_bytes.items()
    }

    configmap_data.update({
        name: decode_text(blob, name)
        for name, blob in artifact_bytes.items()
    })

    configmap_data[
        'processed-writer-input.json'
    ] = decode_text(
        driver_input_bytes,
        'processed-writer-input.json'
    )

    attempt_id = sha(
        inventory_bytes
        + permit_bytes
        + listing_bytes
    )[:24]

    configmap_name = safe_kubernetes_name(
        'visit-proc-runtime-' + attempt_id
    )

    application_name = safe_kubernetes_name(
        'visit-proc-write-' + attempt_id[:20]
    )

    configmap = {
        'apiVersion': 'v1',
        'kind': 'ConfigMap',

        'metadata': {
            'name': configmap_name,
            'namespace': 'dw-spark',

            'labels': {
                'healthcare-task': 'task003',
                'healthcare-purpose':
                    'visit-processed-runtime',
            },
        },

        'immutable': True,

        'data': configmap_data,
    }

    configmap_bytes = (
        json.dumps(
            configmap,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + '\n'
    ).encode('utf-8')

    # Kubernetes objects have a hard size limit.
    # Keep substantial headroom below that limit.
    require(
        len(configmap_bytes) < 750000,
        'ConfigMap JSON exceeds safety budget'
    )

    rendered = (
        template
        .replace(
            '__APP_NAME__',
            application_name
        )
        .replace(
            '__CONFIGMAP_NAME__',
            configmap_name
        )
    )

    require(
        '__' not in rendered,
        'unresolved template placeholder'
    )

    spark_application_bytes = (
        rendered.encode('utf-8')
    )

    state = {
        'task':
            'TASK-003',

        'step':
            'STEP-05G2C2C2B2',

        'status':
            'PREPARED_NOT_CREATED',

        'run_id':
            run_id,

        'attempt_id':
            attempt_id,

        'runtime_configmap_name':
            configmap_name,

        'spark_application_name':
            application_name,

        'runtime_configmap_sha256':
            sha(configmap_bytes),

        'spark_application_sha256':
            sha(spark_application_bytes),

        'write_permit_sha256':
            sha(permit_bytes),

        'fresh_listing_sha256':
            sha(listing_bytes),

        'person_map_fingerprint':
            fingerprint,

        'configmap_created':
            False,

        'spark_application_submitted':
            False,

        's3_write':
            False,

        'postgresql_write':
            False,
    }

    return (
        configmap_bytes,
        spark_application_bytes,
        state,
    )


def read_regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(
            'Missing or unsafe file: ' + str(path)
        )

    return path.read_bytes()


def save_bytes_once(path, blob):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if path.exists():
        if (
            path.is_symlink()
            or path.read_bytes() != blob
        ):
            raise ValueError(
                'Immutable output conflict: '
                + str(path)
            )

        return 'REUSED'

    with path.open('xb') as handle:
        handle.write(blob)

    return 'CREATED'


def main():
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        '--root',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--f2-state',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--run-id',
        required=True,
    )

    parser.add_argument(
        '--fresh-listing',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--write-permit',
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    require(
        args.run_id
        and len(args.run_id) <= 128
        and all(
            char.isalnum()
            or char in '._-'
            for char in args.run_id
        )
        and args.run_id not in ('.', '..'),
        'unsafe run ID'
    )

    root = args.root.resolve()

    base = (
        root
        / 'runtime/reports/task003/step05'
    )

    inventory_path = (
        base
        / 'processed-bundle-inventories'
        / args.run_id
        / 'source-inventory.json'
    )

    plan_path = (
        base
        / 'processed-plans'
        / args.run_id
        / 'plan.json'
    )

    intent_path = (
        base
        / 'processed-intents'
        / args.run_id
        / 'write-intent.json'
    )

    reservation_path = (
        base
        / 'writer-reservations'
        / args.run_id
        / 'reservation-create.json'
    )

    template_path = (
        root
        / 'spark/manifests/task003/'
        'visit-processed-writer.yaml.tpl'
    )

    source_bytes = {
        name:
            read_regular(root / repo_path)

        for name, repo_path
        in SOURCE_PATHS.items()
    }

    inventory_bytes = read_regular(
        inventory_path
    )

    f2_bytes = read_regular(
        args.f2_state
    )

    plan_bytes = read_regular(
        plan_path
    )

    intent_bytes = read_regular(
        intent_path
    )

    reservation_bytes = read_regular(
        reservation_path
    )

    listing_bytes = read_regular(
        args.fresh_listing
    )

    permit_bytes = read_regular(
        args.write_permit
    )

    template_bytes = read_regular(
        template_path
    )

    (
        configmap_bytes,
        spark_application_bytes,
        state,
    ) = build_bundle(
        args.run_id,
        inventory_bytes,
        f2_bytes,
        plan_bytes,
        intent_bytes,
        reservation_bytes,
        listing_bytes,
        permit_bytes,
        source_bytes,
        template_bytes,
    )

    attempt_id = state['attempt_id']

    output = (
        base
        / 'processed-runtime-bundles'
        / args.run_id
        / attempt_id
    )

    configmap_status = save_bytes_once(
        output / 'runtime-configmap.json',
        configmap_bytes,
    )

    application_status = save_bytes_once(
        output / 'sparkapplication.yaml',
        spark_application_bytes,
    )

    state_status = save_once(
        output / 'bundle-state.json',
        state,
    )

    print(
        'RUNTIME_CONFIGMAP_FILE_STATUS='
        + configmap_status
    )

    print(
        'SPARKAPPLICATION_FILE_STATUS='
        + application_status
    )

    print(
        'BUNDLE_STATE_STATUS='
        + state_status
    )

    print(
        'RUNTIME_ATTEMPT_ID='
        + attempt_id
    )

    print(
        'RUNTIME_CONFIGMAP_NAME='
        + state['runtime_configmap_name']
    )

    print(
        'SPARK_APPLICATION_NAME='
        + state['spark_application_name']
    )

    print(
        'RUNTIME_CONFIGMAP_SHA256='
        + state['runtime_configmap_sha256']
    )

    print(
        'SPARK_APPLICATION_SHA256='
        + state['spark_application_sha256']
    )

    print(
        'RUNTIME_BUNDLE_DIR='
        + str(output)
    )

    print('K8S_CONFIGMAP_CREATED=NO')
    print('SPARK_APPLICATION_SUBMITTED=NO')
    print('S3_WRITE=NO')
    print('DATABASE_WRITE=NO')


if __name__ == '__main__':
    main()
PY_APP

# ========================================================
# 3. Unit / negative tests
# ========================================================

cat > "$STAGE/tests/task003/test_visit_processed_runtime_bundle.py" <<'PY_TEST'
import json
import sys
import unittest

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'apps/task003')
)

sys.path.insert(
    0,
    str(ROOT / 'spark/apps/visit')
)


from build_visit_processed_runtime_bundle import (
    SOURCE_PATHS,
    build_bundle,
    sha,
    validate_template,
)


def pack(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
        )
        + '\n'
    ).encode()


class RuntimeBundleTests(unittest.TestCase):

    def setUp(self):
        self.now = datetime(
            2026,
            10,
            9,
            20,
            0,
            tzinfo=timezone.utc,
        )

        self.sources = {
            name:
                (name + '\n').encode()

            for name
            in SOURCE_PATHS
        }

        f2_pins = {
            name:
                sha(self.sources[name])

            for name
            in SOURCE_PATHS

            if name not in (
                'run_visit_processed_writer.py',
                'processed_visit_writer_core.py',
            )
        }

        self.f2 = {
            'task': 'TASK-003',
            'step': 'STEP-05F2',
            'status': 'PASS',

            'input': {
                'mounted_file_sha256':
                    f2_pins,

                'raw_context': {
                    'raw_publish_run_id':
                        'raw-test',
                },

                'expected_persons':
                    2,

                'expected_class_counts': {
                    'ambulatory': 3,
                },
            },

            'result': {
                'candidate_rows': 3,
                'referenced_persons': 2,
            },
        }

        self.f2_bytes = pack(
            self.f2
        )

        base = (
            's3://health-processed/'
            'contract_version=v1/'
            'entity=visit_occurrence/'
            'source=synthea/'
            'source_version=v3.3.0/'
            'ingest_date=2026-10-08/'
            'batch_id=test/'
            'raw_publish_run_id=raw-test/'
            'run_id=test-run'
        )

        self.plan = {
            'task': 'TASK-003',
            'step': 'STEP-05G1',
            'status': 'PLANNED',

            'run_id': 'test-run',

            'base_uri':
                base,

            'data_uri':
                base + '/data/',

            'expected_rows':
                3,

            'expected_persons':
                2,

            'class_counts': {
                'ambulatory': 3,
            },

            'source_f2_evidence_sha256':
                sha(self.f2_bytes),

            'published':
                False,

            'persisted':
                False,

            'visit_ids_allocated':
                0,

            'postgresql_write':
                False,
        }

        self.plan_bytes = pack(
            self.plan
        )

        self.intent = {
            'task': 'TASK-003',
            'step': 'STEP-05G2C1',
            'status':
                'PREFLIGHT_SNAPSHOT_ONLY',

            'run_id':
                'test-run',

            'step05f2_sha256':
                sha(self.f2_bytes),

            'plan_sha256':
                sha(self.plan_bytes),

            'write_authorized':
                False,
        }

        self.intent_bytes = pack(
            self.intent
        )

        prefix = (
            base.split(
                'health-processed/',
                1,
            )[1]
            + '/'
        )

        self.record = {
            'run_id':
                'test-run',

            'bucket':
                'health-processed',

            'prefix':
                prefix,

            'write_intent_sha256':
                sha(self.intent_bytes),

            'plan_sha256':
                sha(self.plan_bytes),

            'write_authorized':
                False,

            'mode':
                'EXCLUSIVE_CREATE_ONLY',
        }

        self.reservation = {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'immutable': True,

            'metadata': {
                'name':
                    'visit-proc-lock-test',

                'namespace':
                    'dw-spark',

                'labels': {
                    'healthcare-task':
                        'task003',

                    'healthcare-purpose':
                        'visit-processed-writer-lock',
                },
            },

            'data': {
                'reservation.json':
                    json.dumps(
                        self.record
                    )
            },
        }

        self.reservation_bytes = pack(
            self.reservation
        )

        self.listing_bytes = pack({
            'RequestCharged': None
        })

        self.permit = {
            'task':
                'TASK-003',

            'step':
                'STEP-05G2C2C',

            'status':
                'AUTHORIZED_FOR_SINGLE_WRITE',

            'write_authorized':
                True,

            'reservation_created_by_k8s_create':
                True,

            'reservation_verified':
                True,

            'fresh_s3_relist_passed':
                True,

            'fresh_prefix_classification':
                'EMPTY',

            'candidate_published':
                False,

            'postgresql_write':
                False,

            'run_id':
                'test-run',

            'data_uri':
                self.plan['data_uri'],

            'plan_sha256':
                sha(self.plan_bytes),

            'intent_sha256':
                sha(self.intent_bytes),

            'reservation_spec_sha256':
                sha(self.reservation_bytes),

            'fresh_listing_sha256':
                sha(self.listing_bytes),

            'reservation_name':
                self.reservation[
                    'metadata'
                ]['name'],

            'reservation_uid':
                (
                    '123e4567-e89b-12d3-'
                    'a456-426614174000'
                ),

            'reservation_resource_version':
                '12345',

            'issued_at_utc':
                (
                    self.now
                    - timedelta(seconds=5)
                ).isoformat(),

            'expires_at_utc':
                (
                    self.now
                    + timedelta(seconds=120)
                ).isoformat(),

            'person_map_fingerprint':
                'a' * 64,
        }

        self.permit_bytes = pack(
            self.permit
        )

        self.inventory = {
            'schema':
                'task003.visit_processed.'
                'bundle_inventory.v1',

            'status':
                'SOURCE_INVENTORY_ONLY',

            'run_id':
                'test-run',

            'reservation_name':
                self.reservation[
                    'metadata'
                ]['name'],

            'future_artifacts_required': [
                'fresh-s3-listing.json',
                'write-permit.json',
            ],

            'source_files': {
                name: {
                    'repo_path':
                        path,

                    'sha256':
                        sha(
                            self.sources[name]
                        ),

                    'size_bytes':
                        len(
                            self.sources[name]
                        ),
                }

                for name, path
                in SOURCE_PATHS.items()
            },

            'static_artifacts': {
                'step05f2-run-state.json': {
                    'sha256':
                        sha(self.f2_bytes),

                    'size_bytes':
                        len(self.f2_bytes),
                },

                'processed-plan.json': {
                    'sha256':
                        sha(self.plan_bytes),

                    'size_bytes':
                        len(self.plan_bytes),
                },

                'processed-write-intent.json': {
                    'sha256':
                        sha(self.intent_bytes),

                    'size_bytes':
                        len(self.intent_bytes),
                },

                'reservation-create.json': {
                    'sha256':
                        sha(
                            self.reservation_bytes
                        ),

                    'size_bytes':
                        len(
                            self.reservation_bytes
                        ),
                },
            },
        }

        self.inventory_bytes = pack(
            self.inventory
        )

        self.template = b'''apiVersion: sparkoperator.k8s.io/v1beta2
kind: SparkApplication
metadata:
  name: __APP_NAME__
  namespace: dw-spark
spec:
  image: spark:3.5.7-python3
  mainApplicationFile: local:///opt/spark/app/run_visit_processed_writer.py
  sparkVersion: "3.5.7"
  restartPolicy:
    type: Never
  sparkConf:
    spark.hadoop.fs.s3a.endpoint: http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333
    spark.hadoop.fs.s3a.path.style.access: "true"
    spark.hadoop.fs.s3a.connection.ssl.enabled: "false"
    spark.hadoop.fs.s3a.aws.credentials.provider: com.amazonaws.auth.EnvironmentVariableCredentialsProvider
    spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version: "2"
  driver:
    serviceAccount: spark-job
    nodeSelector:
      workload: platform
    envFrom:
      - secretRef:
          name: dw-spark-s3-secret
      - secretRef:
          name: dw-spark-omop-secret
  executor:
    nodeSelector:
      workload: platform
  volumes:
    - name: spark-app
      configMap:
        name: __CONFIGMAP_NAME__
'''

    def build(self):
        return build_bundle(
            'test-run',
            self.inventory_bytes,
            self.f2_bytes,
            self.plan_bytes,
            self.intent_bytes,
            self.reservation_bytes,
            self.listing_bytes,
            self.permit_bytes,
            self.sources,
            self.template,
            now=self.now,
        )

    def test_valid_bundle(self):
        configmap_bytes, app_bytes, state = (
            self.build()
        )

        configmap = json.loads(
            configmap_bytes
        )

        self.assertTrue(
            configmap['immutable']
        )

        self.assertEqual(
            len(configmap['data']),
            18,
        )

        self.assertIn(
            'processed-writer-input.json',
            configmap['data'],
        )

        self.assertNotIn(
            b'__APP_NAME__',
            app_bytes,
        )

        self.assertEqual(
            state['status'],
            'PREPARED_NOT_CREATED',
        )

        self.assertFalse(
            state['configmap_created']
        )

    def test_stable(self):
        self.assertEqual(
            self.build(),
            self.build(),
        )

    def test_expired_permit_rejected(self):
        self.permit[
            'expires_at_utc'
        ] = (
            self.now
            - timedelta(seconds=1)
        ).isoformat()

        self.permit_bytes = pack(
            self.permit
        )

        with self.assertRaises(ValueError):
            self.build()

    def test_nonempty_listing_rejected(self):
        self.listing_bytes = pack({
            'Contents': [
                {
                    'Key': 'x',
                    'Size': 1,
                }
            ],

            'KeyCount': 1,
        })

        self.permit[
            'fresh_listing_sha256'
        ] = sha(
            self.listing_bytes
        )

        self.permit_bytes = pack(
            self.permit
        )

        with self.assertRaises(ValueError):
            self.build()

    def test_source_drift_rejected(self):
        self.sources[
            'canonical_gate.py'
        ] = b'changed\n'

        with self.assertRaisesRegex(
            ValueError,
            'source SHA',
        ):
            self.build()

    def test_inventory_drift_rejected(self):
        self.inventory[
            'reservation_name'
        ] = 'other'

        self.inventory_bytes = pack(
            self.inventory
        )

        with self.assertRaises(ValueError):
            self.build()

    def test_bad_fingerprint_rejected(self):
        self.permit[
            'person_map_fingerprint'
        ] = 'bad'

        self.permit_bytes = pack(
            self.permit
        )

        with self.assertRaisesRegex(
            ValueError,
            'fingerprint',
        ):
            self.build()

    def test_template_placeholder_rejected(self):
        with self.assertRaises(ValueError):
            validate_template(
                self.template
                + b'__EXTRA__\n'
            )

    def test_names_are_dns_safe(self):
        _, _, state = self.build()

        self.assertLessEqual(
            len(
                state[
                    'runtime_configmap_name'
                ]
            ),
            63,
        )

        self.assertLessEqual(
            len(
                state[
                    'spark_application_name'
                ]
            ),
            63,
        )

    def test_driver_input_pins_artifacts(self):
        configmap_bytes, _, _ = (
            self.build()
        )

        data = json.loads(
            configmap_bytes
        )['data']

        driver_input = json.loads(
            data[
                'processed-writer-input.json'
            ]
        )

        self.assertEqual(
            set(
                driver_input[
                    'artifact_sha256'
                ]
            ),
            {
                'step05f2-run-state.json',
                'processed-plan.json',
                'processed-write-intent.json',
                'reservation-create.json',
                'fresh-s3-listing.json',
                'write-permit.json',
            },
        )

        self.assertEqual(
            driver_input[
                'person_map_fingerprint'
            ],
            'a' * 64,
        )


if __name__ == '__main__':
    unittest.main()
PY_TEST

# ========================================================
# 4. Permanent future runtime-bundle runner
# ========================================================

cat > "$STAGE/scripts/task003/05g2c2c2b2-prepare-runtime-bundle.sh" <<'RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G2C2C2B2 RUNTIME BUNDLE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "BUNDLE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C2B2 RUNTIME BUNDLE OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ $# -eq 4 ]] || {
  echo "Usage: $0 F2_RUN_STATE PROCESSED_RUN_ID FRESH_S3_LISTING WRITE_PERMIT"
  exit 2
}

PYTHONPATH="$ROOT/apps/task003:$ROOT/spark/apps/visit" \
python3 "$ROOT/apps/task003/build_visit_processed_runtime_bundle.py" \
  --root "$ROOT" \
  --f2-state "$1" \
  --run-id "$2" \
  --fresh-listing "$3" \
  --write-permit "$4"

echo 'RUNTIME_BUNDLE_PREPARED=PASS'
echo 'K8S_CONFIGMAP_CREATED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
RUNNER

# ========================================================
# 5. Syntax and isolated tests
# ========================================================

echo '=== 1. Syntax and unit tests ==='

python3 - "$STAGE" <<'PY_AST'
import ast
import sys

from pathlib import Path

base = Path(sys.argv[1])

for relative in (
    'apps/task003/build_visit_processed_runtime_bundle.py',
    'tests/task003/test_visit_processed_runtime_bundle.py',
):
    ast.parse(
        (base / relative).read_text(),
        filename=relative,
    )

print('RUNTIME_BUNDLE_PYTHON_AST=PASS')
PY_AST

bash -n \
  "$STAGE/scripts/task003/05g2c2c2b2-prepare-runtime-bundle.sh"

cp \
  "$ROOT/apps/task003/plan_visit_processed.py" \
  "$STAGE/apps/task003/plan_visit_processed.py"

cp \
  "$ROOT/spark/apps/visit/processed_visit_writer_core.py" \
  "$STAGE/spark/apps/visit/processed_visit_writer_core.py"

PYTHONPATH="$STAGE/apps/task003:$STAGE/spark/apps/visit" \
python3 -m unittest discover \
  -s "$STAGE/tests/task003" \
  -p 'test_visit_processed_runtime_bundle.py' \
  -v

echo 'RUNTIME_BUNDLE_TESTS=PASS'

# ========================================================
# 6. Verify infrastructure stays aligned with F2C
# ========================================================

echo '=== 2. Verify Spark infrastructure parity with F2C ==='

python3 - \
  "$ROOT/spark/manifests/task003/visit-candidate-preflight.yaml.tpl" \
  "$STAGE/spark/manifests/task003/visit-processed-writer.yaml.tpl" \
  <<'PY_PARITY'
import sys

from pathlib import Path

f2 = Path(sys.argv[1]).read_text()
writer = Path(sys.argv[2]).read_text()

shared = (
    'image: spark:3.5.7-python3',

    'sparkVersion: "3.5.7"',

    (
        'https://repo1.maven.org/maven2/'
        'org/apache/hadoop/hadoop-aws/'
        '3.3.4/hadoop-aws-3.3.4.jar'
    ),

    (
        'https://repo1.maven.org/maven2/'
        'com/amazonaws/aws-java-sdk-bundle/'
        '1.12.262/aws-java-sdk-bundle-1.12.262.jar'
    ),

    (
        'https://repo1.maven.org/maven2/'
        'org/wildfly/openssl/wildfly-openssl/'
        '1.0.7.Final/wildfly-openssl-1.0.7.Final.jar'
    ),

    (
        'https://repo1.maven.org/maven2/'
        'org/postgresql/postgresql/'
        '42.7.4/postgresql-42.7.4.jar'
    ),

    (
        'spark.hadoop.fs.s3a.endpoint: '
        'http://dw-seaweedfs-s3.'
        'dw-seaweedfs.svc.cluster.local:8333'
    ),

    (
        'spark.hadoop.fs.s3a.path.style.access: '
        '"true"'
    ),

    (
        'spark.hadoop.fs.s3a.connection.ssl.enabled: '
        '"false"'
    ),

    (
        'spark.hadoop.fs.s3a.aws.credentials.provider: '
        'com.amazonaws.auth.'
        'EnvironmentVariableCredentialsProvider'
    ),

    (
        'spark.hadoop.mapreduce.'
        'fileoutputcommitter.algorithm.version: "2"'
    ),

    'serviceAccount: spark-job',

    'name: dw-spark-s3-secret',

    'name: dw-spark-omop-secret',

    'workload: platform',
)

for item in shared:
    assert item in f2, (
        'F2C template missing: ' + item
    )

    assert item in writer, (
        'Writer template missing: ' + item
    )

assert writer.count(
    '__APP_NAME__'
) == 1

assert writer.count(
    '__CONFIGMAP_NAME__'
) == 1

assert (
    'mainApplicationFile: '
    'local:///opt/spark/app/'
    'run_visit_processed_writer.py'
) in writer

print(
    'F2C_SPARK_INFRASTRUCTURE_PARITY=PASS'
)

print(
    'WRITER_TEMPLATE_PLACEHOLDERS=PASS'
)
PY_PARITY

# ========================================================
# 7. Canonical conflict check
# ========================================================

echo '=== 3. Canonical conflict check and installation ==='

FILES=(
  apps/task003/build_visit_processed_runtime_bundle.py
  tests/task003/test_visit_processed_runtime_bundle.py
  scripts/task003/05g2c2c2b2-prepare-runtime-bundle.sh
  spark/manifests/task003/visit-processed-writer.yaml.tpl
)

GEN=scripts/task003/05g2c2c2b2-prepare-runtime-bundle-source.sh

for rel in "${FILES[@]}"; do
  if [[ -L "$ROOT/$rel" ]] || {
    [[ -e "$ROOT/$rel" ]] &&
    ! cmp -s "$STAGE/$rel" "$ROOT/$rel"
  }; then

    echo "ERROR: canonical conflict $rel"
    exit 1
  fi
done

if [[ -L "$ROOT/$GEN" ]] || {
  [[ -e "$ROOT/$GEN" ]] &&
  ! cmp -s "$SOURCE" "$ROOT/$GEN"
}; then

  echo "ERROR: canonical generator conflict $GEN"
  exit 1
fi

# ========================================================
# 8. Install canonical source
# ========================================================

for rel in "${FILES[@]}"; do
  mkdir -p "$(dirname "$ROOT/$rel")"

  mode=644

  [[ "$rel" != *.sh ]] || mode=755

  if [[ -f "$ROOT/$rel" ]] &&
     cmp -s "$STAGE/$rel" "$ROOT/$rel"; then

    echo "CANONICAL_SOURCE_REUSED=$rel"

  else
    install \
      -m "$mode" \
      "$STAGE/$rel" \
      "$ROOT/$rel"

    echo "CANONICAL_SOURCE_READY=$rel"
  fi
done

if [[ -f "$ROOT/$GEN" ]]; then

  echo "CANONICAL_GENERATOR_REUSED=$GEN"

else
  install \
    -m 755 \
    "$SOURCE" \
    "$ROOT/$GEN"

  echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo 'STEP05G2C2C2B2_SOURCE_AND_TESTS=PASS'
echo 'RUNTIME_BUNDLE_CREATED=NO'
echo 'K8S_RESOURCE_CREATED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
echo 'GIT_COMMIT=NO'
