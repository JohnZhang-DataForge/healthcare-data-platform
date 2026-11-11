# OpenSpec-Change: deploy-local-ohdsi-atlas
# OpenSpec-Task: 4.0.4; operator-controlled job only.
# Apply with __RUN_ID__ replaced by controlled Self-Runner, never from main.
# Reuses exactly the immutable Achilles image and DB role in the prior official job.
apiVersion: batch/v1
kind: Job
metadata:
  name: atlas3-achilles-visit200201-__RUN_ID__
  namespace: dw-atlas
  labels:
    app.kubernetes.io/name: atlas3-achilles
    app.kubernetes.io/part-of: local-omop-research
    app.kubernetes.io/managed-by: healthcare-data-platform
spec:
  backoffLimit: 0
  completions: 1
  parallelism: 1
  activeDeadlineSeconds: 900
  template:
    metadata:
      labels:
        app.kubernetes.io/name: atlas3-achilles
        app.kubernetes.io/part-of: local-omop-research
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/hostname: worker03
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: achilles
          image: docker.io/ohdsi/broadsea-achilles@sha256:9bae4871c3e1465f1a721fe3215f8a5fec5f2c2928408d9330a64ab32bfd6866
          imagePullPolicy: IfNotPresent
          command: ["Rscript", "/opt/achilles/visit200201.R"]
          securityContext:
            allowPrivilegeEscalation: false
            capabilities: {drop: ["ALL"]}
          env:
            - {name: ACHILLES_SOURCE, value: LOCAL_OMOP}
            - {name: ACHILLES_DB_URI, value: "postgresql://dw-postgre.dw-postgre.svc.cluster.local:5432/omop"}
            - name: ACHILLES_DB_USERNAME
              valueFrom:
                secretKeyRef: {name: atlas-webapi-db, key: app-username}
            - name: ACHILLES_DB_PASSWORD
              valueFrom:
                secretKeyRef: {name: atlas-webapi-db, key: app-password}
            - {name: ACHILLES_CDM_SCHEMA, value: cdm}
            - {name: ACHILLES_VOCAB_SCHEMA, value: cdm}
            - {name: ACHILLES_RES_SCHEMA, value: atlas_results}
            - {name: ACHILLES_CDM_VERSION, value: "5.4"}
            - {name: ACHILLES_NUM_THREADS, value: "1"}
          resources:
            requests: {cpu: 200m, memory: 1Gi}
            limits: {cpu: "1", memory: 4Gi}
          volumeMounts:
            - {name: script, mountPath: /opt/achilles/visit200201.R, subPath: achilles_visit200201_once.R, readOnly: true}
            - {name: scratch, mountPath: /opt/achilles/workspace}
      volumes:
        - name: script
          configMap:
            name: atlas3-achilles-visit200201-script-__RUN_ID__
            defaultMode: 0444
        - name: scratch
          emptyDir: {sizeLimit: 1Gi}
