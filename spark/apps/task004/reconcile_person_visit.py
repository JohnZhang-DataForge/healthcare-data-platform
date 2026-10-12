import argparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, countDistinct, trim

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--patient-uri",required=True)
    p.add_argument("--encounter-uri",required=True)
    p.add_argument("--batch-id",required=True)
    p.add_argument("--expected-patient-rows",type=int,required=True)
    p.add_argument("--expected-encounter-rows",type=int,required=True)
    return p.parse_args()

def require(ok,message):
    if not ok:
        raise RuntimeError(message)

def one_value(df,name):
    rows=[r[name] for r in df.select(name).distinct().collect()]
    require(len(rows)==1,f"{name} must contain exactly one value: {rows}")
    return rows[0]

def main():
    a=parse_args()
    spark=(SparkSession.builder.appName("task004-person-visit-batch-reconciliation").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    try:
        patient=spark.read.parquet(a.patient_uri).cache()
        encounter=spark.read.parquet(a.encounter_uri).cache()
        patient_required={"source_record_id","source_system","source_version","source_batch_id","source_ingest_date"}
        encounter_required={"source_encounter_id","source_person_id","source_system","source_version","source_batch_id","source_ingest_date"}
        require(patient_required.issubset(patient.columns),"Patient processing schema missing reconciliation fields")
        require(encounter_required.issubset(encounter.columns),"Encounter processing schema missing reconciliation fields")
        patient_rows=patient.count()
        encounter_rows=encounter.count()
        patient_unique=patient.agg(countDistinct("source_record_id").alias("n")).first()["n"]
        encounter_unique=encounter.agg(countDistinct("source_encounter_id").alias("n")).first()["n"]
        patient_blank=patient.filter(col("source_record_id").isNull() | (trim(col("source_record_id"))=="")).count()
        encounter_blank=encounter.filter(col("source_encounter_id").isNull() | (trim(col("source_encounter_id"))=="") | col("source_person_id").isNull() | (trim(col("source_person_id"))=="")).count()
        require(patient_rows==a.expected_patient_rows,"Patient row count mismatch")
        require(encounter_rows==a.expected_encounter_rows,"Encounter row count mismatch")
        require(patient_unique==patient_rows,"Patient source_record_id not unique")
        require(encounter_unique==encounter_rows,"Encounter source_encounter_id not unique")
        require(patient_blank==0,"Blank/null Patient key")
        require(encounter_blank==0,"Blank/null Encounter key/reference")
        p_source=one_value(patient,"source_system")
        e_source=one_value(encounter,"source_system")
        p_version=one_value(patient,"source_version")
        e_version=one_value(encounter,"source_version")
        p_batch=one_value(patient,"source_batch_id")
        e_batch=one_value(encounter,"source_batch_id")
        p_date=str(one_value(patient,"source_ingest_date"))
        e_date=str(one_value(encounter,"source_ingest_date"))
        require(p_source==e_source,"source_system mismatch")
        require(p_version==e_version,"source_version mismatch")
        require(p_batch==a.batch_id and e_batch==a.batch_id,"batch_id mismatch")
        require(p_date==e_date,"source_ingest_date mismatch")
        patient_keys=patient.select(col("source_record_id").alias("patient_id")).distinct()
        orphan_count=(encounter.select("source_person_id").distinct().join(patient_keys,col("source_person_id")==col("patient_id"),"left_anti").count())
        referenced_people=encounter.select("source_person_id").distinct().count()
        require(orphan_count==0,"Encounter references Patient not present in same batch")
        require(referenced_people>0,"Encounter references no patients")
        print(f"PATIENT_ROWS={patient_rows}")
        print(f"PATIENT_UNIQUE_IDS={patient_unique}")
        print(f"ENCOUNTER_ROWS={encounter_rows}")
        print(f"ENCOUNTER_UNIQUE_IDS={encounter_unique}")
        print(f"REFERENCED_PATIENTS={referenced_people}")
        print(f"ORPHAN_ENCOUNTERS={orphan_count}")
        print(f"SOURCE_SYSTEM={p_source}")
        print(f"SOURCE_VERSION={p_version}")
        print(f"SOURCE_BATCH_ID={p_batch}")
        print(f"SOURCE_INGEST_DATE={p_date}")
        print("PROCESSING_MUTATION=NO")
        print("POSTGRESQL_MUTATION=NO")
        print("BATCH_RECONCILIATION=PASS")
        print("RESULT=PASS")
    finally:
        spark.stop()
if __name__=="__main__":
    main()
