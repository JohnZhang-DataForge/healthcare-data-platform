apiVersion: v1
kind: Pod
metadata:
  name: __POD_NAME__
  namespace: dw-spark
  labels:
    healthcare-task: task003
    healthcare-purpose: visit-raw-metadata-reader
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  activeDeadlineSeconds: 600
  containers:
    - name: aws
      image: amazon/aws-cli:2.15.57
      imagePullPolicy: IfNotPresent
      command: ["/bin/sh", "-c", "sleep 600"]
      envFrom:
        - secretRef:
            name: dw-spark-s3-secret
