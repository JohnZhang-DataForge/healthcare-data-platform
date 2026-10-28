# REVIEW-ONLY. Never apply automatically from this source file.
# One-shot POST of a freshly generated, frozen Johns Creek FHIR source to OIE.
# The runner must first verify active K8s jobs/Generator PVC, exact Channel
# mapping + internal admin scoped OIE send/read permission and DNS-matching TLS CA.
# On ANY unknown POST result, HOLD and audit persistent OIE; DO NOT rerun.
# Receipts emitted to stdout must be captured by this same authorized Runner
# and committed as a run-scoped immutable ConfigMap for the HL7 Publisher.
apiVersion: batch/v1
kind: Job
metadata:
  name: __OIE_SENDER_JOB_NAME__
  namespace: dw-synthea
  labels:
    app.kubernetes.io/name: johns-creek-oie-sender
    app.kubernetes.io/part-of: healthcare-clinical-producers
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 1200
  template:
    metadata:
      labels:
        app.kubernetes.io/name: johns-creek-oie-sender
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
        - name: oie-sender
          image: __PUBLISHER_IMAGE_DIGEST__
          imagePullPolicy: IfNotPresent
          command: ["python3", "-m", "apps.clinical_producers.oie_message_submit"]
          args:
            - "--state-root"
            - "/synthea-new-generator-state"
            - "--profile"
            - "/config/profile.json"
            - "--request-id"
            - "__SOURCE_REQUEST_ID__"
            - "--run-id"
            - "__RUN_ID__"
            - "--channel-id"
            - "__VERIFIED_OIE_CHANNEL_ID__"
            - "--expected-source-manifest-sha256"
            - "__PINNED_SOURCE_MANIFEST_SHA256__"
          env:
            - name: OIE_INTERNAL_ADMIN_MODE
              value: "1"
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
              memory: 256Mi
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
            - name: oie-trust
              mountPath: /oie-trust/ca.crt
              subPath: ca.crt
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
        - name: oie-trust
          secret:
            secretName: __VERIFIED_OIE_CA_SECRET_NAME__
            defaultMode: 0444
        - name: tmp
          emptyDir:
            sizeLimit: 64Mi
