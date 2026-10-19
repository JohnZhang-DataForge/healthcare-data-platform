# Probe offline regression — 2026-10-19

PR introduces five fake-kubectl tests for the opt-in source collector: positive match with explicit GitSync/driver HOLD, empty Airflow Pods, incorrect ConfigMap identity, mismatched Python bytes, and unsafe relative report path. Fake kubectl is installed only into an ephemeral PATH; it cannot contact Kubernetes. Gate executes Python unittest and Bash source checks. No live evidence claimed. Task 4.4 PARTIAL and Task 4.9 HOLD.
