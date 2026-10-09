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
