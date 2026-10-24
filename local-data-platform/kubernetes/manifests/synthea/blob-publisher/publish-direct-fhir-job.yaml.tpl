# STATIC DIRECT FHIR Job template, intended ONLY for dw-synthea on worker01.
# Source is the EXISTING Generator PVC, read-only in the same Namespace.
# No extra Publisher PVC and no source transfer between Namespaces.
# Template requires an authorized Runner: image digest, source Request/Manifest SHA,
# scoped Azure identity Secret, vetted Profile, Account URL/Container/Prefix.
# No cluster or Azure writes on merge.
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
