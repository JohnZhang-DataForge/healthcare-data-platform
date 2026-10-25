"""Independent HL7 decoder/readback tests, no OIE or cloud access."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from apps.clinical_producers.oie.hl7_readback import (
    Hl7ReadbackError, parse_adt_a01, verify_adt_against_fhir
)

PATIENT_ID="patient-one"
ENCOUNTER_ID="enc-one"
AUTH="JOHNSCREEKB"
HOSP="johns-creek-hospital-b"
FEED="johns-creek-hospital-b-hl7-v2"
REQUEST="johnscreek-fhir-0001"
CONTROL="-".join((HOSP,FEED,REQUEST,ENCOUNTER_ID,"A01"))
TIME="20261024131530+0000"


def sample():
    msh="MSH|^~\\&|SYNTHEA_SIM|JOHNSCREEKB|LANDING|SYNTHETIC|"+TIME+"||ADT^A01^ADT_A01|"+CONTROL+"|P|2.5.1"
    evn="EVN|A01|"+TIME
    pid="PID|1||"+PATIENT_ID+"^^^JOHNSCREEKB^MR||Synthetic\\F\\Patient^Hospital\\S\\B"
    pv1="PV1|1|I"+"|"*16+"|"+ENCOUNTER_ID+"^^^JOHNSCREEKB^VN"+"|"*24+"|"+TIME
    # Canonical PV1 positional fields use a list to prevent accidental off-by-one.
    p=["PV1","1","I"]+[""]*42
    p[19]=ENCOUNTER_ID+"^^^JOHNSCREEKB^VN"
    p[44]=TIME
    return "\r".join((msh,evn,pid,"|".join(p)))+"\r"


def source():
    return {"request_id":REQUEST,"bundle":{"resourceType":"Bundle","type":"collection","entry":[
        {"fullUrl":"urn:uuid:patient-one","resource":{"resourceType":"Patient","id":PATIENT_ID}},
        {"resource":{"resourceType":"Encounter","id":ENCOUNTER_ID,
          "class":{"system":"http://terminology.hl7.org/CodeSystem/v3-ActCode","code":"IMP"},
          "status":"finished","subject":{"reference":"urn:uuid:patient-one"},
          "period":{"start":"2026-10-24T09:15:30-04:00"}}}
    ]}}


class Readback(unittest.TestCase):
    def test_parse_genuine_segment_indexes(self):
        value=parse_adt_a01(sample())
        self.assertEqual(value["control_id"],CONTROL)
        self.assertEqual(value["patient_id"],PATIENT_ID)
        self.assertEqual(value["encounter_id"],ENCOUNTER_ID)
        self.assertEqual(value["event_time"],TIME)

    def test_source_correlation(self):
        self.assertEqual(verify_adt_against_fhir(
            sample().encode(),source(),hospital_id=HOSP,feed_id=FEED,
            assigning_authority=AUTH)["encounter_id"],ENCOUNTER_ID)

    def test_ambulatory_never_accepted_as_admission(self):
        item=source();item["bundle"]["entry"][1]["resource"]["class"]["code"]="AMB"
        with self.assertRaisesRegex(Hl7ReadbackError,"FHIR_NOT_ADMISSION"):
            verify_adt_against_fhir(sample(),item,hospital_id=HOSP,feed_id=FEED,
                                    assigning_authority=AUTH)

    def test_corruption_invalid_encoding_or_segments_block(self):
        cases=[
          sample().replace("|2.5.1\r","|2.3\r"),
          sample().replace("ADT^A01^ADT_A01","ADT^A04^ADT_A04"),
          sample().replace("PV1|1|I","PV1|1|O"),
          sample().replace(TIME,"20260101000000+0000",1),
          sample().replace(CONTROL,"NOT_EXPECTED\nINJECTED"),
          sample().replace("PID|1||","PID|1||bad^^^OTHER^MR|",1),
          sample()[:-1],
          sample()+"Z",
        ]
        for case in cases:
            with self.subTest(case=case[-45:]):
                with self.assertRaises(Hl7ReadbackError):
                    parse_adt_a01(case)
        with self.assertRaises(Hl7ReadbackError):
            parse_adt_a01(b"\xff")

    def test_control_and_timestamp_must_match_source(self):
        with self.assertRaisesRegex(Hl7ReadbackError,"FHIR_HL7_CONTROL_MISMATCH"):
            verify_adt_against_fhir(sample(),{**source(),"request_id":"another"},
                                   hospital_id=HOSP,feed_id=FEED,assigning_authority=AUTH)
        item=source()
        item["bundle"]["entry"][1]["resource"]["period"]["start"]="2026-10-25T09:15:30-04:00"
        with self.assertRaisesRegex(Hl7ReadbackError,"FHIR_HL7_TIME_MISMATCH"):
            verify_adt_against_fhir(sample(),item,hospital_id=HOSP,feed_id=FEED,
                                   assigning_authority=AUTH)


if __name__=="__main__":unittest.main()
