workspace_id  = ""
pipeline_name = "pl_omop_snapshot_to_onelake"

# PLAN-only bootstrap: pipeline contains an explicit Fail activity.
# Once the Notebook exists and its ETL is implemented, supply its *real*
# Fabric item GUID here; that is a separate, reviewed change.
notebook_id = ""
