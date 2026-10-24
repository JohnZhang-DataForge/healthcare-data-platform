# TEMPLATE ONLY. Render exact __JOB_NAME__, __IMAGE_DIGEST__, __REQUEST_CONFIGMAP__.
# ConfigMap key request.json must come from externally validated hospital Profile.
# No cluster mutation is permitted by merely adding this file to Main.
apiVersion: batch/v1
kind: Job
metadata:
  name: __JOB_NAME__
  namespace: dw-synthea
  labels:
    app.kubernetes.io/name: synthea-new-generator
    app.kubernetes.io/part-of: healthcare-data-platform
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 1800
  template:
    metadata:
      labels:
        app.kubernetes.io/name: synthea-new-generator
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
        - name: generator
          image: __IMAGE_DIGEST__
          imagePullPolicy: IfNotPresent
          args:
            - "--request"
            - "/inputs/request.json"
            - "--state-root"
            - "/synthea-new-generator-state"
          env:
            - name: HOME
              value: /tmp
            - name: JAVA_TOOL_OPTIONS
              value: "-Djava.io.tmpdir=/tmp"
          resources:
            requests:
              cpu: 250m
              memory: 1Gi
              ephemeral-storage: 512Mi
            limits:
              cpu: "2"
              memory: 5Gi
              ephemeral-storage: 2Gi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: request
              mountPath: /inputs
              readOnly: true
            - name: state
              mountPath: /synthea-new-generator-state
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: request
          configMap:
            name: __REQUEST_CONFIGMAP__
            defaultMode: 0444
            items:
              - key: request.json
                path: request.json
        - name: state
          persistentVolumeClaim:
            claimName: synthea-new-generator-state
        - name: tmp
          emptyDir:
            sizeLimit: 1Gi
