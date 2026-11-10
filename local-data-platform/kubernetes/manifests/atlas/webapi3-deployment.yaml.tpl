apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapi3
  namespace: dw-atlas
  labels: {app.kubernetes.io/name: webapi3}
spec:
  replicas: 1
  revisionHistoryLimit: 2
  strategy: {type: Recreate}
  selector:
    matchLabels: {app.kubernetes.io/name: webapi3}
  template:
    metadata:
      labels: {app.kubernetes.io/name: webapi3}
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/hostname: worker03
        workload: compute
      terminationGracePeriodSeconds: 40
      securityContext:
        seccompProfile: {type: RuntimeDefault}
      containers:
        - name: webapi3
          image: __WEBAPI3_IMAGE_DIGEST__
          imagePullPolicy: IfNotPresent
          ports: [{name: http, containerPort: 8080}]
          env:
            - {name: DATASOURCE_DRIVERCLASSNAME, value: org.postgresql.Driver}
            - {name: DATASOURCE_URL, value: "jdbc:postgresql://__PG17_CLUSTERIP_SERVICE__:5432/omop?currentSchema=webapi"}
            - {name: DATASOURCE_OHDSI_SCHEMA, value: webapi}
            - {name: SPRING_JPA_PROPERTIES_HIBERNATE_DEFAULT_SCHEMA, value: webapi}
            - {name: SPRING_BATCH_REPOSITORY_TABLEPREFIX, value: webapi.batch_}
            - name: DATASOURCE_USERNAME
              valueFrom: {secretKeyRef: {name: atlas-webapi-db, key: app-username}}
            - name: DATASOURCE_PASSWORD
              valueFrom: {secretKeyRef: {name: atlas-webapi-db, key: app-password}}
            - name: SPRING_FLYWAY_USER
              valueFrom: {secretKeyRef: {name: atlas-webapi-db, key: migration-username}}
            - name: SPRING_FLYWAY_PASSWORD
              valueFrom: {secretKeyRef: {name: atlas-webapi-db, key: migration-password}}
            - {name: SPRING_FLYWAY_SCHEMAS, value: webapi}
            - {name: SPRING_FLYWAY_PLACEHOLDERS_OHDSISCHEMA, value: webapi}
            - {name: SPRING_FLYWAY_BASELINE_VERSION, value: "3.0.0"}
            - {name: SPRING_FLYWAY_TABLE, value: flyway_schema_history}
            - {name: SPRING_FLYWAY_URL, value: "jdbc:postgresql://__PG17_CLUSTERIP_SERVICE__:5432/omop?currentSchema=webapi"}
            - {name: SECURITY_CORS_ENABLED, value: "true"}
            - {name: SECURITY_CORS_ALLOWED_ORIGINS, value: "https://atlas.johnzhang-dataforge.site"}
            - {name: SECURITY_AUTH_DB_ENABLED, value: "true"}
            - {name: SECURITY_AUTH_OIDC_ENABLED, value: "false"}
            - {name: SECURITY_AUTH_DB_DATASOURCE_URL, value: "jdbc:postgresql://__PG17_CLUSTERIP_SERVICE__:5432/omop?currentSchema=webapi"}
            - name: SECURITY_AUTH_DB_DATASOURCE_USERNAME
              valueFrom: {secretKeyRef: {name: atlas-webapi-db, key: app-username}}
            - name: SECURITY_AUTH_DB_DATASOURCE_PASSWORD
              valueFrom: {secretKeyRef: {name: atlas-webapi-db, key: app-password}}
            - {name: SECURITY_AUTH_DB_DATASOURCE_SCHEMA, value: webapi}
            - {name: SECURITY_ALLOWANONYMOUSACCESS, value: "false"}
            - name: SECURITY_JWT_SECRET
              valueFrom: {secretKeyRef: {name: atlas-webapi-db, key: jwt-secret}}
            - {name: TREXSQL_ENABLED, value: "false"}
            - {name: JAVA_TOOL_OPTIONS, value: "-XX:MaxRAMPercentage=70 -Djava.io.tmpdir=/tmp"}
          readinessProbe:
            httpGet: {path: /WebAPI/info, port: http}
            initialDelaySeconds: 45
            periodSeconds: 15
            timeoutSeconds: 8
            failureThreshold: 12
          livenessProbe:
            httpGet: {path: /WebAPI/info, port: http}
            initialDelaySeconds: 110
            periodSeconds: 30
            timeoutSeconds: 10
          resources:
            requests: {cpu: 250m, memory: 1Gi}
            limits: {cpu: "2", memory: 3Gi}
          securityContext:
            allowPrivilegeEscalation: false
            capabilities: {drop: ["ALL"]}
          volumeMounts:
            - {name: tmp, mountPath: /tmp}
            - {name: webapi-cache, mountPath: /data}
      volumes:
        - name: tmp
          emptyDir: {sizeLimit: 512Mi}
        - name: webapi-cache
          emptyDir: {sizeLimit: 1Gi}
