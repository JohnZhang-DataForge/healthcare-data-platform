# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "environment": {
# META       "environmentId": "ed219dd5-b5ec-8517-46ed-8da0d85a4218",
# META       "workspaceId": "00000000-0000-0000-0000-000000000000"
# META     }
# META   }
# META }

# CELL ********************

# Git-created onboarding smoke only; no FHIR, Blob, Lakehouse or Delta access.
import importlib.metadata as metadata
import healthcare_data_engine as engine
import pyspark

assert metadata.version("healthcare-data-engine") == "0.1.1"
assert engine.__version__ == "0.1.1"
assert pyspark.__version__.startswith("4.1")
print("FABRIC_GIT_NOTEBOOK_RUNTIME_IMPORT_CHECKS_PASSED")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

notebookutils.notebook.exit("FABRIC_GIT_NEW_NB_ENGINE_011_SPARK41_PASS_20261102")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
