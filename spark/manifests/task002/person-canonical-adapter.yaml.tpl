apiVersion: sparkoperator.k8s.io/v1beta2
kind: SparkApplication

metadata:
  name: __APP_NAME__
  namespace: dw-spark

  labels:
    healthcare-task: task002
    healthcare-domain: person
    healthcare-step: canonical-adapter

spec:
  type: Python
  mode: cluster

  image: spark:3.5.7-python3
  imagePullPolicy: IfNotPresent

  mainApplicationFile: local:///opt/spark/app/synthea_patient_adapter.py

  arguments:
    - --manifest-uri
    - __MANIFEST_URI__

    - --batch-id
    - __BATCH_ID__

    - --run-id
    - __RUN_ID__

    - --processing-data-uri
    - __PROCESSING_DATA_URI__

    - --contract-path
    - /opt/spark/app/patient-v1.json

  sparkVersion: "3.5.7"

  restartPolicy:
    type: Never

  deps:
    packages:
      - org.apache.hadoop:hadoop-aws:3.3.4

  sparkConf:
    spark.jars.ivy: /tmp/.ivy2

    spark.hadoop.fs.s3a.endpoint: http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333
    spark.hadoop.fs.s3a.path.style.access: "true"
    spark.hadoop.fs.s3a.connection.ssl.enabled: "false"
    spark.hadoop.fs.s3a.endpoint.region: us-east-1
    spark.hadoop.fs.s3a.aws.credentials.provider: com.amazonaws.auth.EnvironmentVariableCredentialsProvider

    spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version: "2"

    spark.kubernetes.driver.ownPersistentVolumeClaim: "false"
    spark.kubernetes.driver.reusePersistentVolumeClaim: "false"

  driver:
    cores: 1
    coreLimit: "1"
    memory: 1g

    serviceAccount: spark-job

    nodeSelector:
      workload: platform

    envFrom:
      - secretRef:
          name: dw-spark-s3-secret

    volumeMounts:
      - name: spark-app
        mountPath: /opt/spark/app
        readOnly: true

  executor:
    instances: 1
    cores: 1
    coreLimit: "1"
    memory: 1g

    nodeSelector:
      workload: platform

    envFrom:
      - secretRef:
          name: dw-spark-s3-secret

    volumeMounts:
      - name: spark-app
        mountPath: /opt/spark/app
        readOnly: true

  volumes:
    - name: spark-app
      configMap:
        name: __CONFIGMAP_NAME__
