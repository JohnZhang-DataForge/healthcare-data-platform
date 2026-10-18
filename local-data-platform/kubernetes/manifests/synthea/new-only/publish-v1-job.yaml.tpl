# NEW_ONLY verified S3 publication from existing frozen PVC (no Generator/Writer).
# Source/PG historical key gate MUST be completed before phase=publish.
apiVersion: batch/v1
kind: Job
metadata:
  name: __JOB_NAME__
  namespace: dw-synthea
  labels:
    app.kubernetes.io/name: synthea-new-only-publisher
    app.kubernetes.io/part-of: healthcare-data-platform
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 1200
  template:
    metadata:
      labels:
        app.kubernetes.io/name: synthea-new-only-publisher
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
        - name: publisher
          image: ghcr.io/johnzhang-dataforge/healthcare-data-platform-synthea@sha256:2dc1e4283eb194e548b245842987ff403bf8e092a70f473fdf6fa5a1c547816d
          imagePullPolicy: IfNotPresent
          command: ["/bin/sh", "-ec"]
          args: [__COMMAND_JSON__]
          resources:
            requests:
              cpu: "250m"
              memory: "1Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          env:
            - name: S3_ENDPOINT
              value: "http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333"
            - name: S3_BUCKET_LANDING
              value: "health-landing"
            - name: AWS_DEFAULT_REGION
              value: "us-east-1"
            - name: NEW_ONLY_READONLY_SOURCE_AUDIT
              value: "PASS"
            - name: NEW_ONLY_PG_SOURCE_AUDIT
              value: "PASS"
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: dw-synthea-s3-secret
                  key: AWS_ACCESS_KEY_ID
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: dw-synthea-s3-secret
                  key: AWS_SECRET_ACCESS_KEY
          volumeMounts:
            - name: state
              mountPath: /synthea-state
              readOnly: true
            - name: scripts
              mountPath: /audit
              readOnly: true
            - name: scratch
              mountPath: /work
      volumes:
        - name: state
          persistentVolumeClaim:
            claimName: synthea-new-only-state
            readOnly: true
        - name: scripts
          configMap:
            name: __CONFIGMAP_NAME__
        - name: scratch
          emptyDir: {}
