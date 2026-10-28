# STATIC / REVIEW-ONLY. Never deploy this template directly.
# Requires a NEW frozen Johns Creek Request and same-run OIE POST receipts
# from a trusted controller. This job only GETs exact new message IDs and PUTs
# immutable HL7 bytes to approved Azure Blob after complete source validation.
# This YAML cannot prove receipt provenance, deploy/update OIE Channel or mint
# scoped OIE credentials/trusted CA; those are separate HARD HOLD gates.
apiVersion: batch/v1
kind: Job
metadata:
  name: __PUBLISHER_JOB_NAME__
  namespace: dw-synthea
  labels:
    app.kubernetes.io/name: azure-hl7-publisher
    app.kubernetes.io/part-of: healthcare-clinical-producers
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 1500
  template:
    metadata:
      labels:
        app.kubernetes.io/name: azure-hl7-publisher
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
        - name: hl7-publisher
          image: __PUBLISHER_IMAGE_DIGEST__
          imagePullPolicy: IfNotPresent
          command: ["python3", "-m", "apps.clinical_producers.hl7_blob_runtime"]
          args:
            - "--state-root"
            - "/synthea-new-generator-state"
            - "--profile"
            - "/config/profile.json"
            - "--request-id"
            - "__SOURCE_REQUEST_ID__"
            - "--receipts"
            - "/receipts/new-oie-receipts.json"
            - "--run-id"
            - "__RUN_ID__"
            - "--channel-id"
            - "__VERIFIED_OIE_CHANNEL_ID__"
            - "--assigning-authority"
            - "JOHNSCREEKB"
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
            - name: OIE_SCOPED_USERNAME
              valueFrom:
                secretKeyRef:
                  name: __SCOPED_OIE_SECRET_NAME__
                  key: username
            - name: OIE_SCOPED_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: __SCOPED_OIE_SECRET_NAME__
                  key: password
            - name: OIE_TRUSTED_CA_FILE
              value: /oie-trust/ca.crt
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
              ephemeral-storage: 256Mi
            limits:
              cpu: "1"
              memory: 1Gi
              ephemeral-storage: 1Gi
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
            - name: receipts
              mountPath: /receipts/new-oie-receipts.json
              subPath: new-oie-receipts.json
              readOnly: true
            - name: oie-trust
              mountPath: /oie-trust
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
        - name: receipts
          configMap:
            name: __SAME_RUN_OIE_RECEIPTS_CONFIGMAP__
            defaultMode: 0444
            items:
              - key: new-oie-receipts.json
                path: new-oie-receipts.json
        - name: oie-trust
          secret:
            secretName: __VERIFIED_OIE_CA_SECRET_NAME__
            defaultMode: 0444
        - name: tmp
          emptyDir:
            sizeLimit: 64Mi
