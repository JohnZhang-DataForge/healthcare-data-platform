# Fabric notebook source

# METADATA ********************
# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************
# Parameters for a later Data Factory Notebook activity.
export_id = ""
manifest_uri = ""

# METADATA ********************
# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark",
# META   "is_parameter": true
# META }

# CELL ********************
# Infrastructure bootstrap ONLY. Never acknowledge a snapshot as loaded
# until the separate exporter, DQ, and idempotent OneLake writer are built.
raise RuntimeError(
    "OMOP OneLake notebook is an infrastructure bootstrap. "
    "Data loading is intentionally disabled pending ETL implementation."
)

# METADATA ********************
# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
