apiVersion: sparkoperator.k8s.io/v1beta2
kind: SparkApplication

metadata:
  name: __APP_NAME__
  namespace: dw-spark

  labels:
    healthcare-task: task003
    healthcare-domain: visit
    healthcare-step: encounter-canonical-adapter

spec:
  type: Python
  mode: cluster

  image: spark:3.5.7-python3
  imagePullPolicy: IfNotPresent

  mainApplicationFile: local:///opt/spark/app/synthea_encounter_adapter.py

  arguments:
    - --input-uri
    - __INPUT_URI__

    - --output-data-uri
    - __OUTPUT_DATA_URI__

    - --contract-path
    - /opt/spark/app/encounter-v1.json

    - --expected-rows
    - "__EXPECTED_ROWS__"

    - --source-system
    - __SOURCE_SYSTEM__

    - --source-version
    - __SOURCE_VERSION__

    - --source-batch-id
    - __SOURCE_BATCH_ID__

    - --source-ingest-date
    - __SOURCE_INGEST_DATE__

    - --source-file
    - __SOURCE_FILE__

    - --source-file-sha256
    - __SOURCE_FILE_SHA256__

    - --source-file-size-bytes
    - "__SOURCE_FILE_SIZE_BYTES__"

    - --processing-run-id
    - __PROCESSING_RUN_ID__

  sparkVersion: "3.5.7"

  restartPolicy:
    type: Never

  deps:
    jars:
      - https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar
      - https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar
      - https://repo1.maven.org/maven2/org/wildfly/openssl/wildfly-openssl/1.0.7.Final/wildfly-openssl-1.0.7.Final.jar

  sparkConf:
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
