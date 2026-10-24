apiVersion: batch/v1
kind: Job

metadata:
  name: __JOB_NAME__
  namespace: dw-synthea

  labels:
    app.kubernetes.io/name: synthea-generator
    app.kubernetes.io/part-of: healthcare-data-platform
    healthcare-data-platform/task: task004
    healthcare-data-platform/runtime: generate-only

spec:
  backoffLimit: 0

  template:
    metadata:
      labels:
        app.kubernetes.io/name: synthea-generator
        healthcare-data-platform/task: task004
        healthcare-data-platform/runtime: generate-only

    spec:
      restartPolicy: Never
      automountServiceAccountToken: false

      nodeSelector:
        kubernetes.io/hostname: worker01

      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001

        seccompProfile:
          type: RuntimeDefault

      containers:
        - name: synthea-generator

          image: __IMAGE_REF_JSON__
          imagePullPolicy: IfNotPresent

          securityContext:
            allowPrivilegeEscalation: false

            capabilities:
              drop:
                - ALL

          resources:
            requests:
              cpu: "250m"
              memory: "1Gi"

            limits:
              cpu: "2"
              memory: "4Gi"

          env:
            - name: BATCH_ID
              value: __BATCH_ID_JSON__

            - name: POPULATION_SIZE
              value: __POPULATION_SIZE_JSON__

            - name: SEED
              value: __SEED_JSON__

            - name: CLINICIAN_SEED
              value: __CLINICIAN_SEED_JSON__

            - name: REFERENCE_DATE
              value: __REFERENCE_DATE_JSON__

            - name: STATE
              value: __STATE_JSON__

            - name: CITY
              value: __CITY_JSON__

          command:
            - /bin/bash
            - -lc

          args:
            - |
              set -Eeuo pipefail

              echo "GENERATE_ONLY_CONTAINER_START=YES"

              /usr/local/bin/healthcare-synthea-generator

              python3 - <<'PY'
              import hashlib
              import json
              from pathlib import Path

              manifest_path = Path(
                  "/work/evidence/manifest.draft.json"
              )

              validation_path = Path(
                  "/work/evidence/validation.json"
              )

              manifest = json.loads(
                  manifest_path.read_text(
                      encoding="utf-8"
                  )
              )

              validation = json.loads(
                  validation_path.read_text(
                      encoding="utf-8"
                  )
              )

              if manifest.get("status") != (
                  "LOCAL_VALIDATED_NOT_UPLOADED"
              ):
                  raise SystemExit(
                      "ERROR: unexpected draft "
                      "manifest status"
                  )

              if validation.get("status") != "PASS":
                  raise SystemExit(
                      "ERROR: local validation "
                      "status is not PASS"
                  )

              if validation.get(
                  "validated_file_count"
              ) != 18:
                  raise SystemExit(
                      "ERROR: validated_file_count "
                      "is not 18"
                  )

              files = manifest.get("files")

              if (
                  not isinstance(files, list)
                  or len(files) != 18
              ):
                  raise SystemExit(
                      "ERROR: draft manifest must "
                      "contain exactly 18 files"
                  )

              names = [
                  Path(item["path"]).name
                  for item in files
              ]

              if len(names) != len(set(names)):
                  raise SystemExit(
                      "ERROR: duplicate file names "
                      "in draft manifest"
                  )

              patients = next(
                  (
                      item
                      for item in files
                      if Path(item["path"]).name
                      == "patients.csv"
                  ),
                  None,
              )

              if patients is None:
                  raise SystemExit(
                      "ERROR: patients.csv missing "
                      "from draft manifest"
                  )

              fingerprint = hashlib.sha256()

              for item in sorted(
                  files,
                  key=lambda value:
                      Path(value["path"]).name,
              ):
                  filename = Path(
                      item["path"]
                  ).name

                  row_count = item[
                      "row_count"
                  ]

                  size_bytes = item[
                      "size_bytes"
                  ]

                  sha256 = item[
                      "sha256"
                  ]

                  print(
                      "FILE_EVIDENCE|"
                      f"{filename}|"
                      f"{row_count}|"
                      f"{size_bytes}|"
                      f"{sha256}"
                  )

                  fingerprint.update(
                      (
                          filename
                          + "|"
                          + sha256
                          + "\n"
                      ).encode("utf-8")
                  )

              print(
                  "MANIFEST_STATUS="
                  + manifest["status"]
              )

              print(
                  "VALIDATION_REPORT_STATUS="
                  + validation["status"]
              )

              print(
                  "VALIDATED_FILE_COUNT="
                  + str(
                      validation[
                          "validated_file_count"
                      ]
                  )
              )

              print(
                  "PATIENT_ROWS="
                  + str(
                      patients[
                          "row_count"
                      ]
                  )
              )

              print(
                  "PAYLOAD_FINGERPRINT="
                  + fingerprint.hexdigest()
              )

              print(
                  "LANDING_PUBLICATION="
                  "NOT_STARTED"
              )

              print(
                  "GENERATE_ONLY_RUNTIME=PASS"
              )
              PY
