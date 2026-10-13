"""TASK004 read-only CDM runtime entrypoint.

Only validates a dynamic batch plan. This entrypoint deliberately has no
database connection, SQL execution or commit capability.
"""
import argparse
import json
from pathlib import Path
from task004_cdm_materialization_plan import plan

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-file", required=True)
    args = parser.parse_args()
    supplied = json.loads(Path(args.plan_file).read_text(encoding="utf-8"))
    keys = ("batch_id", "manifest_sha256", "manifest_uri",
            "person_processing_uri", "visit_processing_uri",
            "person_rows", "visit_rows", "source_version")
    original = {key: supplied[key] for key in keys}
    original.update(state="HANDOFF_VERIFIED_NOT_LOADED",
                    cdm_write_permitted=False)
    verified = plan(original)
    if verified["plan_sha256"] != supplied.get("plan_sha256"):
        raise ValueError("BLOCKED=plan_drift")
    if supplied.get("database_mutation_authorized") is not False:
        raise ValueError("BLOCKED=database_mutation_forbidden")
    print("DYNAMIC_CDM_PLAN_VALIDATED=PASS")
    print("DATABASE_MUTATION=NO")

if __name__ == "__main__":
    main()
