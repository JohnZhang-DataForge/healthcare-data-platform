# DO NOT APPLY WITHOUT USER AUTHORIZATION + LIVE PREFLIGHT.
# DEBUG ONLY: ephemeral Derby/config state; no PVC, no PG, no legacy paths.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oie-debug
  namespace: dw-oie
  labels:
    app.kubernetes.io/name: oie-debug
    app.kubernetes.io/component: fhir-to-hl7-poc
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app.kubernetes.io/name: oie-debug
  template:
    metadata:
      labels:
        app.kubernetes.io/name: oie-debug
    spec:
      nodeSelector:
        kubernetes.io/hostname: worker01
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
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
              drop: ["ALL"]
          ports:
            - name: admin-https
              containerPort: 8443
              protocol: TCP
          resources:
            requests:
              cpu: 250m
              memory: 1Gi
              ephemeral-storage: 512Mi
            limits:
              cpu: "2"
              memory: 4Gi
              ephemeral-storage: 4Gi
          startupProbe:
            tcpSocket: {port: admin-https}
            periodSeconds: 10
            failureThreshold: 90
          readinessProbe:
            tcpSocket: {port: admin-https}
            periodSeconds: 10
            failureThreshold: 6
          volumeMounts:
            - name: debug-appdata
              mountPath: /opt/engine/appdata
            - name: debug-bootstrap
              mountPath: /run/secrets/mirth_properties
              subPath: mirth_properties
              readOnly: true
      volumes:
        - name: debug-appdata
          emptyDir:
            sizeLimit: 4Gi
        - name: debug-bootstrap
          secret:
            secretName: oie-debug-bootstrap
            defaultMode: 0440
