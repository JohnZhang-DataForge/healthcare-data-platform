apiVersion: batch/v1
kind: Job
metadata:
  name: __JOB_NAME__
  namespace: dw-synthea
  labels:
    app.kubernetes.io/name: synthea-new-only
    app.kubernetes.io/part-of: healthcare-data-platform
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 1200
  template:
    metadata:
      labels:
        app.kubernetes.io/name: synthea-new-only
    spec:
      nodeSelector:
        kubernetes.io/hostname: worker01
      restartPolicy: Never
      automountServiceAccountToken: false
      securityContext:
        runAsUser: 10001
        runAsGroup: 10001
        runAsNonRoot: true
        fsGroup: 10001
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: synthea-new-only
        image: __IMAGE_REF__
        imagePullPolicy: IfNotPresent
        command: ["python3", "/opt/synthea-new-only/generate_new_only.py"]
        env:
        - name: GENERATION_REQUEST_ID
          value: __REQUEST_ID__
        - name: SYNTHEA_STATE_ROOT
          value: /synthea-state
        resources:
          requests: {cpu: 250m, memory: 1Gi}
          limits: {cpu: "2", memory: 4Gi}
        securityContext:
          allowPrivilegeEscalation: false
          capabilities: {drop: ["ALL"]}
        volumeMounts:
        - {name: state, mountPath: /synthea-state}
        - {name: generator-code, mountPath: /opt/synthea-new-only, readOnly: true}
      volumes:
      - name: state
        persistentVolumeClaim:
          claimName: synthea-new-only-state
      - name: generator-code
        configMap:
          name: __CONFIGMAP_NAME__
          items:
          - {key: generate_new_only.py, path: generate_new_only.py}
