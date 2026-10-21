# Fabric notebook source

# METADATA ********************
# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# CELL ********************
# No data sources, cloud writes, secrets, Spark actions, or Lakehouse mutations.
# This smoke proves notebook execution, not the OMOP replication E2E.
from datetime import datetime, timezone

print("#### FABRIC_TRIAL_NOTEBOOK_SMOKE_OUTPUT_BEGIN ####")
print("NOTEBOOK=nb_trial_smoke")
print("MODE=NO_DATA_WRITE")
print("UTC_EXECUTION_TIME=" + datetime.now(timezone.utc).isoformat())
print("FABRIC_NOTEBOOK_SMOKE=PASS")
print("#### FABRIC_TRIAL_NOTEBOOK_SMOKE_OUTPUT_END ####")
