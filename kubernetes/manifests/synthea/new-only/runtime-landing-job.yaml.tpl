# Publication/reading phases. Source and PostgreSQL source-id audits MUST be
# completed independently before the two __AUDIT_*__ values are set to PASS.
# The flags are not DB authorization, and never bypass Writer drift checks.
apiVersion: batch/v1
kind: Job
metadata:
  name: __JOB_NAME__
  namespace: dw-synthea
  labels: {app.kubernetes.io/name: synthea-new-only-landing}
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 600
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/hostname: worker01}
      securityContext: {runAsNonRoot: true, runAsUser: 10001, runAsGroup: 10001, fsGroup: 10001, seccompProfile: {type: RuntimeDefault}}
      containers:
      - name: landing
        image: __IMAGE_DIGEST__
        imagePullPolicy: Always
        args: ["--phase", "__PHASE__", "--request-id", "__REQUEST_ID__"]
        resources:
          requests: {cpu: 250m, memory: 1Gi}
          limits: {cpu: "2", memory: 4Gi}
        securityContext: {allowPrivilegeEscalation: false, capabilities: {drop: ["ALL"]}}
        env:
        - {name: S3_ENDPOINT, value: "http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333"}
        - {name: S3_BUCKET_LANDING, value: "health-landing"}
        - {name: AWS_DEFAULT_REGION, value: "us-east-1"}
        - {name: AWS_EC2_METADATA_DISABLED, value: "true"}
        - {name: NEW_ONLY_READONLY_SOURCE_AUDIT, value: "__AUDIT_S3__"}
        - {name: NEW_ONLY_PG_SOURCE_AUDIT, value: "__AUDIT_PG__"}
        - name: AWS_ACCESS_KEY_ID
          valueFrom: {secretKeyRef: {name: dw-synthea-s3-secret, key: AWS_ACCESS_KEY_ID}}
        - name: AWS_SECRET_ACCESS_KEY
          valueFrom: {secretKeyRef: {name: dw-synthea-s3-secret, key: AWS_SECRET_ACCESS_KEY}}
        volumeMounts:
        - {name: state, mountPath: /synthea-state, readOnly: true}
        - {name: scratch, mountPath: /work}
      volumes:
      - {name: state, persistentVolumeClaim: {claimName: synthea-new-only-state, readOnly: true}}
      - {name: scratch, emptyDir: {}}
