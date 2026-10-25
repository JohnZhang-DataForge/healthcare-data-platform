"""Hospital-neutral immutable Azure Blob plan schema/byte gates (no Azure)."""
import hashlib, json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from apps.clinical_producers.blob_publish_contract import (
    BlobPlanRejected, verified_plan, load_plan_json, VERSION
)

def fhir_plan():
    raw=json.dumps({"resourceType":"Bundle","entry":[]},sort_keys=True).encode()
    name="fhir/patient-one.json"
    plan={"schema_version":VERSION,"hospital_id":"atlanta-hospital-a",
          "feed_id":"atlanta-hospital-a-fhir-r4","request_id":"atlanta-20261024-0001",
          "source_manifest_sha256":"a"*64,"target_format":"FHIR_R4",
          "verification_state":"SOURCE_HANDOFF_VERIFIED","skipped_non_admissions":0,
          "objects":[{"name":name,"size_bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),
                      "source_event_id":None}]}
    return plan,{name:raw}

class BlobPlanTests(unittest.TestCase):
    def test_fhir_validated_bytes_yield_stable_hospital_route_key(self):
        plan,content=fhir_plan()
        result=verified_plan(plan,content,landing_prefix="healthcare/v1")
        self.assertEqual(result[0]["blob_key"],"healthcare/v1/atlanta-hospital-a/atlanta-hospital-a-fhir-r4/atlanta-20261024-0001/FHIR_R4/fhir/patient-one.json")
        self.assertEqual(result,verified_plan(plan,content,landing_prefix="healthcare/v1"))
    def test_changed_bytes_and_undeclared_data_fail(self):
        plan,data=fhir_plan()
        key=next(iter(data))
        with self.assertRaisesRegex(BlobPlanRejected,"SOURCE_BYTES_MISMATCH"):
            verified_plan(plan,{key:b"tampered"},landing_prefix="healthcare")
        with self.assertRaisesRegex(BlobPlanRejected,"UNDECLARED_SOURCE_BYTES"):
            verified_plan(plan,{**data,"fhir/extra.json":b"bad"},landing_prefix="healthcare")
    def test_unsafe_key_and_wrong_hospital_fail(self):
        p,d=fhir_plan()
        p["objects"][0]["name"]="fhir/../x.json"
        with self.assertRaisesRegex(BlobPlanRejected,"UNSAFE_OR_DUPLICATE_OBJECT_NAME"):
            verified_plan(p,d,landing_prefix="healthcare")
        p,d=fhir_plan()
        p["hospital_id"]="../demo"
        with self.assertRaisesRegex(BlobPlanRejected,"INVALID_SOURCE_ID"):
            verified_plan(p,d,landing_prefix="healthcare")
    def test_unverified_wrong_format_and_prefix_fail(self):
        p,d=fhir_plan()
        p["verification_state"]="OIE_HL7_READBACK_VERIFIED"
        with self.assertRaisesRegex(BlobPlanRejected,"UNVERIFIED_DELIVERY_STATE"):
            verified_plan(p,d,landing_prefix="healthcare")
        p,d=fhir_plan()
        with self.assertRaisesRegex(BlobPlanRejected,"INVALID_LANDING_PREFIX"):
            verified_plan(p,d,landing_prefix="../../unsafe")

    def test_demo_placeholder_rejected_before_blob_key_creation(self):
        for key in ("hospital_id", "feed_id"):
            p, data = fhir_plan()
            p[key] = "demo-placeholder"
            with self.assertRaisesRegex(BlobPlanRejected, "DEMO_HOSPITAL_FEED_ID_RESERVED"):
                verified_plan(p, data, landing_prefix="healthcare")

    def test_hl7_a01_strict_positive_and_control_id_conflict(self):
        control="johns-creek-hospital-b-johns-creek-hospital-b-hl7-v2-johnscreek-20261024-0001-enc-one-A01"
        moment="20261024131530+0000"
        fields=["PV1","1","I"]+[""]*42
        fields[19]="enc-one^^^JOHNSCREEKB^VN"
        fields[44]=moment
        wire="\r".join((
            "MSH|^~\\&|SYNTHEA_SIM|JOHNSCREEKB|LANDING|SYNTHETIC|"+moment+
            "||ADT^A01^ADT_A01|"+control+"|P|2.5.1",
            "EVN|A01|"+moment,
            "PID|1||patient-one^^^JOHNSCREEKB^MR||Demo^Patient",
            "|".join(fields)))+"\r"
        raw=wire.encode()
        name="hl7/enc-one.hl7"
        plan={"schema_version":VERSION,"hospital_id":"johns-creek-hospital-b",
              "feed_id":"johns-creek-hospital-b-hl7-v2",
              "request_id":"johnscreek-20261024-0001",
              "source_manifest_sha256":"b"*64,"target_format":"HL7_V2",
              "verification_state":"OIE_HL7_READBACK_VERIFIED","skipped_non_admissions":30,
              "objects":[{"name":name,"sha256":hashlib.sha256(raw).hexdigest(),
                          "size_bytes":len(raw),"source_event_id":control}]}
        result=verified_plan(plan,{name:raw},landing_prefix="healthcare")
        self.assertTrue(result[0]["blob_key"].endswith("/HL7_V2/hl7/enc-one.hl7"))
        plan["objects"][0]["source_event_id"]="another"
        with self.assertRaisesRegex(BlobPlanRejected,"HL7_CONTROL_ID_MISMATCH"):
            verified_plan(plan,{name:raw},landing_prefix="healthcare")

    def test_noncanonical_alias_paths_fail_closed(self):
        for alias in ("fhir//patient-one.json","fhir/./patient-one.json"):
            plan,data=fhir_plan()
            plan["objects"][0]["name"]=alias
            with self.assertRaisesRegex(BlobPlanRejected,"UNSAFE_OR_DUPLICATE_OBJECT_NAME"):
                verified_plan(plan,data,landing_prefix="healthcare")

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(BlobPlanRejected,"DUPLICATE_JSON_KEY"):
            load_plan_json('{"schema_version":"a","schema_version":"b"}')
    def test_hl7_cannot_assume_source_verified_or_fabric_complete(self):
        p,_=fhir_plan()
        p["target_format"]="HL7_V2"
        with self.assertRaisesRegex(BlobPlanRejected,"UNVERIFIED_DELIVERY_STATE"):
            verified_plan(p,{},landing_prefix="healthcare")
        p,d=fhir_plan();p["extra"]=True
        with self.assertRaisesRegex(BlobPlanRejected,"INVALID_PLAN_SHAPE"):
            verified_plan(p,d,landing_prefix="healthcare")

if __name__=="__main__": unittest.main()
