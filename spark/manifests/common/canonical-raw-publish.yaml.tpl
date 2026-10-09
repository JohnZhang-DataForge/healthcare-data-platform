apiVersion: sparkoperator.k8s.io/v1beta2
kind: SparkApplication

metadata:
  name: __APP_NAME__
  namespace: dw-spark

  labels:
    healthcare-task: __TASK_LABEL__
    healthcare-entity: __ENTITY__
    healthcare-step: canonical-raw-publish

spec:
  type: Python
  mode: cluster

  image: spark:3.5.7-python3
  imagePullPolicy: IfNotPresent

  mainApplicationFile: local:///opt/spark/app/publish_canonical_entity.py

  arguments:
    - --input-manifest-uri
    - __INPUT_MANIFEST_URI__

    - --batch-id
    - __BATCH_ID__

    - --processing-run-id
    - __PROCESSING_RUN_ID__

    - --processing-data-uri
    - __PROCESSING_DATA_URI__

    - --raw-data-uri
    - __RAW_DATA_URI__

    - --contract-path
    - /opt/spark/app/__CONTRACT_FILE__

    - --entity
    - __ENTITY__

    - --dataset
    - __DATASET__

    - --source-file-name
    - __SOURCE_FILE_NAME__

    - --expected-adapter-name
    - __EXPECTED_ADAPTER_NAME__

    - --adapter-version
    - __ADAPTER_VERSION__

    - --canonical-version
    - __CANONICAL_VERSION__

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
