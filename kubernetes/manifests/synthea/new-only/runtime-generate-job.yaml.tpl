# Standalone NEW_ONLY generator: no S3 credentials or Airflow dependencies.
apiVersion: batch/v1
kind: Job
metadata:
  name: __JOB_NAME__
  namespace: dw-synthea
  labels: {app.kubernetes.io/name: synthea-new-only}
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 1200
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/hostname: worker01}
      securityContext: {runAsNonRoot: true, runAsUser: 10001, runAsGroup: 10001, fsGroup: 10001, seccompProfile: {type: RuntimeDefault}}
      containers:
      - name: generator
        image: __IMAGE_DIGEST__
        imagePullPolicy: Always
        args: ["--phase", "generate", "--request-id", "__REQUEST_ID__"]
        resources:
          requests: {cpu: 250m, memory: 1Gi}
          limits: {cpu: "2", memory: 4Gi}
        securityContext: {allowPrivilegeEscalation: false, capabilities: {drop: ["ALL"]}}
        volumeMounts: [{name: state, mountPath: /synthea-state}]
      volumes:
      - name: state
        persistentVolumeClaim: {claimName: synthea-new-only-state}
