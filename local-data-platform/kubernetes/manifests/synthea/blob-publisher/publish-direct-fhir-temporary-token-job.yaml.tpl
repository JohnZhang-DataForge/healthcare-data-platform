# STATIC one-shot DIRECT FHIR Publisher Job; NEVER apply without a fresh,
# verified Azure Storage audience token minted by the authorized Workflow.
# GH OIDC JWT / GITHUB_TOKEN are NOT Azure Storage access tokens.
# __SESSION_SECRET_NAME__ MUST be an already created unique, short-lived
# dw-synthea Secret with keys access-token and expires-on; delete after the
# exact Job and readback. Reject token age/expiry in Publisher runtime.
# No extra PVC, and no historical FHIR/OIE message replay.
apiVersion: batch/v1
kind: Job
metadata:
  name: __PUBLISHER_JOB_NAME__
  namespace: dw-synthea
  labels:
    app.kubernetes.io/name: azure-blob-publisher
    app.kubernetes.io/part-of: healthcare-clinical-producers
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 1200
  template:
    metadata:
      labels:
        app.kubernetes.io/name: azure-blob-publisher
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
          image: __PUBLISHER_IMAGE_DIGEST__
          imagePullPolicy: IfNotPresent
          args:
            - "--state-root"
            - "/synthea-new-generator-state"
            - "--profile"
            - "/config/profile.json"
            - "--request-id"
            - "__SOURCE_REQUEST_ID__"
            - "--source-mode"
            - "direct-readonly-pvc"
            - "--expected-source-manifest-sha256"
            - "__PINNED_SOURCE_MANIFEST_SHA256__"
            - "--landing-prefix"
            - "__APPROVED_LANDING_PREFIX__"
          env:
            - name: AZURE_AUTH_MODE
              value: temporary-access-token
            - name: AZURE_BLOB_ACCOUNT_URL
              value: __APPROVED_AZURE_ACCOUNT_URL__
            - name: AZURE_BLOB_CONTAINER
              value: __APPROVED_AZURE_CONTAINER__
            - name: AZURE_STORAGE_BEARER_TOKEN
              valueFrom:
                secretKeyRef:
                  name: __SESSION_SECRET_NAME__
                  key: access-token
            - name: AZURE_STORAGE_TOKEN_EXPIRES_ON
              valueFrom:
                secretKeyRef:
                  name: __SESSION_SECRET_NAME__
                  key: expires-on
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
              ephemeral-storage: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
              ephemeral-storage: 3Gi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: generator-source
              mountPath: /synthea-new-generator-state
              readOnly: true
            - name: profile
              mountPath: /config/profile.json
              subPath: profile.json
              readOnly: true
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: generator-source
          persistentVolumeClaim:
            claimName: synthea-new-generator-state
            readOnly: true
        - name: profile
          configMap:
            name: __VERIFIED_HOSPITAL_PROFILE_CONFIGMAP__
            defaultMode: 0444
            items:
              - key: profile.json
                path: profile.json
        - name: tmp
          emptyDir:
            sizeLimit: 256Mi
