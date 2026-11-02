# STATIC / NEVER AUTO-APPLY. Read-only PG cdm snapshot -> immutable Azure Blob.
# Deployment must replace ALL placeholders with reviewed values (including digests).
# Namespace is dw-synthea for reuse of the EXISTING Blob Publisher/identity;
# PostgreSQL lives in dw-postgre. No Synthea Generator PVC is mounted.
apiVersion: batch/v1
kind: Job
metadata:
  name: __OMOP_SNAPSHOT_JOB_NAME__
  namespace: dw-synthea
  labels:
    app.kubernetes.io/name: omop-blob-snapshot
    app.kubernetes.io/part-of: healthcare-data-platform
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 1800
  ttlSecondsAfterFinished: 86400
  template:
    metadata:
      labels:
        app.kubernetes.io/name: omop-blob-snapshot
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      # Validate node name/resource capacity at execution time; no forced PVC pin.
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      initContainers:
        - name: omop-cdm-readonly-dump
          image: __POSTGRES_17_IMAGE_DIGEST__
          imagePullPolicy: IfNotPresent
          command: ["pg_dump"]
          args:
            - "--format=custom"
            - "--no-owner"
            - "--no-privileges"
            - "--schema=cdm"
            - "--file=/snapshot/omop-cdm.dump"
          env:
            - name: PGHOST
              value: __VERIFIED_OMOP_POSTGRES_SERVICE_DNS__
            - name: PGPORT
              value: "__VERIFIED_OMOP_POSTGRES_PORT__"
            - name: PGDATABASE
              value: __VERIFIED_OMOP_DB_NAME__
            - name: PGUSER
              valueFrom:
                secretKeyRef:
                  name: omop-snapshot-reader
                  key: username
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: omop-snapshot-reader
                  key: password
            - name: PGOPTIONS
              value: "-c default_transaction_read_only=on -c statement_timeout=900000"
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests: {cpu: 100m, memory: 128Mi, ephemeral-storage: 512Mi}
            limits: {cpu: "1", memory: 512Mi, ephemeral-storage: 1Gi}
          volumeMounts:
            - name: snapshot
              mountPath: /snapshot
      containers:
        - name: azure-omop-snapshot-publisher
          image: __PUBLISHER_IMAGE_DIGEST__
          imagePullPolicy: IfNotPresent
          command: ["python3", "-m", "apps.clinical_producers.omop_snapshot_runtime"]
          args:
            - "--dump-path"
            - "/snapshot/omop-cdm.dump"
            - "--snapshot-id"
            - "__UNIQUE_OMOP_SNAPSHOT_ID__"
            - "--blob-prefix"
            - "omop/snapshots"
          env:
            - name: AZURE_AUTH_MODE
              value: "client-secret"
            - name: AZURE_BLOB_ACCOUNT_URL
              value: __APPROVED_AZURE_ACCOUNT_URL__
            - name: AZURE_BLOB_CONTAINER
              value: __APPROVED_AZURE_CONTAINER__
            - name: AZURE_TENANT_ID
              valueFrom:
                secretKeyRef:
                  name: azure-blob-publisher-identity
                  key: tenant-id
            - name: AZURE_CLIENT_ID
              valueFrom:
                secretKeyRef:
                  name: azure-blob-publisher-identity
                  key: client-id
            - name: AZURE_CLIENT_SECRET
              valueFrom:
                secretKeyRef:
                  name: azure-blob-publisher-identity
                  key: client-secret
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests: {cpu: 100m, memory: 256Mi, ephemeral-storage: 512Mi}
            limits: {cpu: "1", memory: 1Gi, ephemeral-storage: 1Gi}
          volumeMounts:
            - name: snapshot
              mountPath: /snapshot
              readOnly: true
      volumes:
        - name: snapshot
          emptyDir:
            sizeLimit: 512Mi
