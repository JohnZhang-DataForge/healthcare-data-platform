# A4 STATIC TEMPLATE ONLY. NEVER kubectl apply before TASK004 owner confirms idle.
# Render with render.py. ConfigMap will be generated alongside this resource.
apiVersion: sparkoperator.k8s.io/v1beta2
kind: SparkApplication
metadata:
  name: portal-a4-__RUN_TOKEN__
  namespace: dw-spark
  labels:
    app.kubernetes.io/name: portal-a4-spark-probe
    app.kubernetes.io/part-of: platform-portal
    platform-portal-phase: a4
spec:
  type: Python
  mode: cluster
  image: spark:3.5.7-python3
  imagePullPolicy: IfNotPresent
  sparkVersion: "3.5.7"
  mainApplicationFile: local:///opt/spark/portal-a4/probe.py
  arguments:
    - --run-token
    - __RUN_TOKEN__
    - --input-uri
    - file:///opt/spark/portal-a4/input.csv
  restartPolicy:
    type: Never
  deps:
    # Candidate pinned exactly to the existing Airflow OpenLineage Python 1.47.1.
    # Runtime Spark/Scala binary + JAR resolution MUST be verified at A4 LIVE gate.
    packages:
      - io.openlineage:openlineage-spark_2.12:1.47.1
  sparkConf:
    spark.jars.ivy: /tmp/.ivy2
    spark.extraListeners: io.openlineage.spark.agent.OpenLineageSparkListener
    spark.openlineage.transport.type: http
    spark.openlineage.transport.url: http://marquez.dw-marquez.svc.cluster.local
    spark.openlineage.transport.endpoint: /api/v1/lineage
    spark.openlineage.transport.timeoutInMillis: "5000"
    spark.openlineage.namespace: healthcare-platform-spark-probe
    spark.sql.shuffle.partitions: "1"
  driver:
    cores: 1
    coreLimit: "1"
    memory: 1g
    serviceAccount: spark-job
    nodeSelector:
      workload: platform
    volumeMounts:
      - name: probe-src
        mountPath: /opt/spark/portal-a4
        readOnly: true
  executor:
    instances: 1
    cores: 1
    coreLimit: "1"
    memory: 1g
    nodeSelector:
      workload: platform
    volumeMounts:
      - name: probe-src
        mountPath: /opt/spark/portal-a4
        readOnly: true
  volumes:
    - name: probe-src
      configMap:
        name: portal-a4-__RUN_TOKEN__-source
