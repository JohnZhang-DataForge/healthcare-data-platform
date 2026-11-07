"""Independent local Spark session checks physical Delta and dbt Candidate."""
import json,os,sys
from pathlib import Path
from urllib.parse import urlparse
APP=Path(__file__).resolve().parents[5]/"local-data-platform/spark/apps/hl7"
sys.path.insert(0,str(APP))
from write_staging_delta import _spark,_warehouse
ROOT=Path(__file__).resolve().parents[5]

def main():
    spark=_spark(_warehouse(os.environ["HL7_LOCAL_WAREHOUSE_URI"]))
    try:
        for table in ("hl7_staging.hl7_events",
            "hl7_candidate.canonical_patient","hl7_candidate.canonical_encounter"):
            d=spark.sql(f"DESCRIBE DETAIL {table}").first().asDict()
            u=urlparse(d["location"])
            assert d["format"]=="delta" and u.scheme in ("","file")
            assert (Path(u.path)/"_delta_log").is_dir(),table
        staging=spark.table("hl7_staging.hl7_events")
        person=spark.table("hl7_candidate.canonical_patient")
        visit=spark.table("hl7_candidate.canonical_encounter")
        assert (staging.count(),person.count(),visit.count())==(2,1,1)
        for entity,df in (("patient",person),("encounter",visit)):
            contract=json.loads((ROOT/f"local-data-platform/spark/contracts/canonical/{entity}-v1.json").read_text())
            expected=[(x["name"],x["type"]) for x in contract["fields"]]
            actual=[(x.name,x.dataType.simpleString()) for x in df.schema.fields]
            assert actual==expected,(entity,actual,expected)
            for field in contract["fields"]:
                if not field["nullable"]:
                    assert df.where(df[field["name"]].isNull()).count()==0
        row=person.select("source_system","source_record_id","race_code","ethnicity_code").first()
        assert tuple(row)==("johns-creek-hl7","patient-one","2028-9","2135-2")
        row=visit.select("source_system","source_person_id","source_encounter_id","source_code").first()
        assert tuple(row)==("johns-creek-hl7","patient-one","visit-one","IMP")
        assert visit.where("start_datetime>end_datetime").count()==0
        print("HL7_LOCAL_DELTA_DBT_CANDIDATE_18_27_CONTRACT=PASS")
        print("HL7_APPROVED_SILVER_AND_GOLD=NO")
    finally: spark.stop()
if __name__=="__main__": main()
