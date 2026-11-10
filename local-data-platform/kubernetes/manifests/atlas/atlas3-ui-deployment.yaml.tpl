apiVersion: apps/v1
kind: Deployment
metadata:
  name: atlas3-ui
  namespace: dw-atlas
  labels:
    app.kubernetes.io/name: atlas3-ui
spec:
  replicas: 1
  revisionHistoryLimit: 2
  strategy: {type: Recreate}
  selector:
    matchLabels: {app.kubernetes.io/name: atlas3-ui}
  template:
    metadata:
      labels: {app.kubernetes.io/name: atlas3-ui}
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/hostname: worker03
        workload: compute
      terminationGracePeriodSeconds: 20
      securityContext:
        runAsUser: 10001
        runAsGroup: 10001
        runAsNonRoot: true
        fsGroup: 10001
        seccompProfile: {type: RuntimeDefault}
      containers:
        - name: atlas3-ui
          image: ghcr.io/johnzhang-dataforge/healthcare-data-platform-atlas3-ui@sha256:cb18de851c4510908de7272a51b72d992f10c1250f170541be929b43789df3c9
          imagePullPolicy: IfNotPresent
          ports: [{name: http, containerPort: 8080}]
          readinessProbe:
            httpGet: {path: /atlas/, port: http}
            periodSeconds: 10
            timeoutSeconds: 4
          livenessProbe:
            httpGet: {path: /atlas/, port: http}
            periodSeconds: 20
            timeoutSeconds: 4
          resources:
            requests: {cpu: 50m, memory: 128Mi}
            limits: {cpu: "500m", memory: 512Mi}
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: {drop: ["ALL"]}
          volumeMounts:
            - {name: caddyfile, mountPath: /etc/caddy/Caddyfile, subPath: Caddyfile, readOnly: true}
            - {name: caddy-data, mountPath: /data}
            - {name: caddy-config, mountPath: /config}
      volumes:
        - name: caddyfile
          configMap: {name: atlas3-frontend-gateway}
        - name: caddy-data
          emptyDir: {sizeLimit: 128Mi}
        - name: caddy-config
          emptyDir: {sizeLimit: 16Mi}
