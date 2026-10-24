# STATIC TEMPLATE ONLY; do not apply without coordinated resource gate.
# The StorageClass must be independently verified to provision on worker01,
# with a RETAIN reclaim policy. Neither StorageClass nor PVC may be deleted by a rerun.
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: oie-state
  namespace: dw-oie
  labels:
    app.kubernetes.io/name: oie
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: __OIE_WORKER01_STORAGE_CLASS__
  resources:
    requests:
      storage: 10Gi
