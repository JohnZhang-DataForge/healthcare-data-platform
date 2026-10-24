# STATIC DIRECT FHIR TEMPLATE ONLY; no Pod, Secret or Azure writes on merge.
# Runtime must render/validate all __PLACEHOLDERS__ from a fresh approved
# source SHA and exact immutable published image digest. OIE HL7 NOT wired.
# The dw-az-blob Publisher cannot directly mount the dw-synthea Generator PVC.
# A separate authorized Runner transfers checked bytes into emptyDir and
# writes /handoff/.ready as exactly BLOB_HANDOFF_READY_V1 followed by LF.
apiVersion: batch/v1
kind: Job
metadata:
  name: __PUBLISHER_JOB_NAME__
  namespace: dw-az-blob
  labels:
    app.kubernetes.io/name: azure-blob-publisher
    app.kubernetes.io/part-of: healthcare-clinical-producers
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 1500
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
            - "/handoff"
            - "--profile"
            - "/config/profile.json"
            - "--request-id"
            - "__SOURCE_REQUEST_ID__"
            - "--ready-marker"
            - "/handoff/.ready"
            - "--expected-source-manifest-sha256"
            - "__PINNED_SOURCE_MANIFEST_SHA256__"
            - "--landing-prefix"
            - "__APPROVED_LANDING_PREFIX__"
            - "--ready-timeout-seconds"
            - "900"
          env:
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
            - name: staging
              mountPath: /handoff
            - name: profile
              mountPath: /config/profile.json
              subPath: profile.json
              readOnly: true
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: staging
          emptyDir:
            sizeLimit: 2Gi
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
