apiVersion: batch/v1
kind: Job

metadata:
  name: __JOB_NAME__
  namespace: dw-synthea

  labels:
    app.kubernetes.io/name: synthea-generator
    app.kubernetes.io/part-of: healthcare-data-platform
    healthcare-data-platform/task: task004
    healthcare-data-platform/runtime: generate-publish

spec:
  backoffLimit: 0

  template:
    metadata:
      labels:
        app.kubernetes.io/name: synthea-generator
        healthcare-data-platform/task: task004
        healthcare-data-platform/runtime: generate-publish

    spec:
      restartPolicy: Never
      automountServiceAccountToken: false

      nodeSelector:
        kubernetes.io/hostname: worker01

      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001

        seccompProfile:
          type: RuntimeDefault

      containers:
        - name: synthea-generator

          image: __IMAGE_REF_JSON__
          imagePullPolicy: IfNotPresent

          securityContext:
            allowPrivilegeEscalation: false

            capabilities:
              drop:
                - ALL

          resources:
            requests:
              cpu: "250m"
              memory: "1Gi"

            limits:
              cpu: "2"
              memory: "4Gi"

          envFrom:
            - secretRef:
                name: dw-synthea-s3-secret

          env:
            - name: BATCH_ID
              value: __BATCH_ID_JSON__

            - name: POPULATION_SIZE
              value: __POPULATION_SIZE_JSON__

            - name: SEED
              value: __SEED_JSON__

            - name: CLINICIAN_SEED
              value: __CLINICIAN_SEED_JSON__

            - name: REFERENCE_DATE
              value: __REFERENCE_DATE_JSON__

            - name: STATE
              value: __STATE_JSON__

            - name: CITY
              value: __CITY_JSON__

            - name: S3_ENDPOINT
              value: "http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333"

            - name: S3_BUCKET_LANDING
              value: "health-landing"

            - name: AWS_DEFAULT_REGION
              value: "us-east-1"

            - name: LANDING_INGEST_DATE
              value: __INGEST_DATE_JSON__

          volumeMounts:
            - name: publisher-source
              mountPath: /opt/task004
              readOnly: true

          command:
            - /bin/bash
            - -lc

          args:
            - |
              set -Eeuo pipefail

              echo "TASK004_GENERATE_PUBLISH_CONTAINER_START=YES"

              /usr/local/bin/healthcare-synthea-generator

              python3 \
                /opt/task004/publish_synthea_landing.py \
                --source-dir /work/output/csv \
                --draft /work/evidence/manifest.draft.json \
                --batch-id "$BATCH_ID" \
                --endpoint "$S3_ENDPOINT" \
                --bucket "$S3_BUCKET_LANDING" \
                --region "$AWS_DEFAULT_REGION" \
                --default-ingest-date "$LANDING_INGEST_DATE" \
                --report /work/evidence/landing-publication.json

              echo "TASK004_GENERATE_PUBLISH_RUNTIME=PASS"

      volumes:
        - name: publisher-source
          configMap:
            name: __CONFIGMAP_NAME__
