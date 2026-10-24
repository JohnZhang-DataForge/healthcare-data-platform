# UNDEPLOYED TEMPLATE. Render only from controlled workflow and exact immutable digest.
# Requires manually provisioned Secret `oie-bootstrap-properties` in dw-oie:
#   key: mirth_properties (contents supplied out of band, never committed)
# The official OIE 4.7.0 configure-from-env script reads /run/secrets/mirth_properties.
# The same script MUTATES /opt/engine/conf/mirth.properties: do not set readOnlyRootFilesystem
# until an image-specific writable config strategy is tested.
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: oie
  namespace: dw-oie
  labels:
    app.kubernetes.io/name: oie
spec:
  replicas: 1
  serviceName: oie
  selector:
    matchLabels:
      app.kubernetes.io/name: oie
  updateStrategy:
    type: RollingUpdate
  template:
    metadata:
      labels:
        app.kubernetes.io/name: oie
    spec:
      # In this PoC every OIE Pod MUST stay on worker01.
      nodeSelector:
        kubernetes.io/hostname: worker01
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        # Numeric UID/GID are REQUIRED from the exact pinned image inspect;
        # upstream USER is named 'engine' and kubelet may reject runAsNonRoot
        # without an explicitly verified numeric runAsUser.
        runAsUser: __OIE_ENGINE_UID__
        runAsGroup: __OIE_ENGINE_GID__
        fsGroup: __OIE_ENGINE_GID__
        seccompProfile:
          type: RuntimeDefault
      terminationGracePeriodSeconds: 120
      containers:
        - name: oie
          image: __OIE_PINNED_IMAGE_DIGEST__
          imagePullPolicy: IfNotPresent
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
          ports:
            - name: https-admin
              containerPort: 8443
              protocol: TCP
          resources:
            requests:
              cpu: 500m
              memory: 2Gi
            limits:
              cpu: "2"
              memory: 4Gi
          startupProbe:
            tcpSocket:
              port: https-admin
            periodSeconds: 10
            failureThreshold: 60
          readinessProbe:
            tcpSocket:
              port: https-admin
            periodSeconds: 10
            failureThreshold: 6
          volumeMounts:
            - name: appdata
              mountPath: /opt/engine/appdata
            - name: bootstrap-secret
              mountPath: /run/secrets/mirth_properties
              subPath: mirth_properties
              readOnly: true
      volumes:
        - name: appdata
          persistentVolumeClaim:
            claimName: oie-state
        - name: bootstrap-secret
          secret:
            secretName: oie-bootstrap-properties
            # Group-readable only; kubelet applies fsGroup for mounted Secret files.
            defaultMode: 0440
