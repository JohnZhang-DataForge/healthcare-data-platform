"""Offline tests only — Channel REST deployment is a separate live gate."""
from pathlib import Path
import sys,unittest
import xml.etree.ElementTree as ET
import json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from apps.clinical_producers.oie.build_channel import render_channel,CHANNEL_ID,CHANNEL_NAME
from apps.clinical_producers.oie.fhir_events import events_from_bundle

class ChannelBuildTests(unittest.TestCase):
 def test_importable_channel_xml_and_script(self):
  result=render_channel()
  root=ET.fromstring(result)
  self.assertEqual(root.findtext("id"),CHANNEL_ID)
  self.assertEqual(root.findtext("name"),CHANNEL_NAME)
  self.assertEqual(root.findtext("sourceConnector/transformer/inboundDataType"),"RAW")
  self.assertEqual(root.findtext("sourceConnector/transportName"),"Channel Reader")
  self.assertEqual(root.findtext("properties/initialState"),"STARTED")
  s=root.findtext("preprocessingScript")
  self.assertIn("fhirToAdtA01",s)
  self.assertIn('JSON.parse(String(message))',s)
  self.assertIn('demo-johns-creek-hl7-v2',s)
  self.assertIn('OIE_ADT_NON_INPATIENT_SKIPPED',s)
  self.assertNotIn("<id>62af393b-ff61-47ec-b5fa-ccd2cd08ce55</id>",result)
 def test_patient_encounter_slices_preserve_source_and_inpatient_logic_not_here(self):
  person={"resourceType":"Patient","id":"patient1"}
  a={"resourceType":"Encounter","id":"visit1","subject":{"reference":"urn:uuid:p1"},"class":{"code":"AMB"}}
  b={"resourceType":"Encounter","id":"visit2","subject":{"reference":"urn:uuid:p1"},"class":{"code":"IMP"}}
  payload={"resourceType":"Bundle","entry":[{"fullUrl":"urn:uuid:p1","resource":person},{"resource":a},{"resource":b}]}
  encoded=json.dumps(payload,sort_keys=True)
  e=events_from_bundle(payload,"johns-creek-001")
  self.assertEqual(len(e),2)
  self.assertEqual([x["bundle"]["entry"][1]["resource"]["id"] for x in e],["visit1","visit2"])
  self.assertEqual(encoded,json.dumps(payload,sort_keys=True))
  self.assertEqual(e[0]["bundle"]["entry"][0]["resource"]["id"],"patient1")
 def test_missing_patient_blocks_not_fabricated(self):
  b={"resourceType":"Bundle","entry":[{"resource":{"resourceType":"Encounter","id":"x","subject":{"reference":"Patient/nope"}}}]}
  with self.assertRaisesRegex(ValueError,"ENCOUNTER_PATIENT_NOT_PRESENT"):
   events_from_bundle(b,"johns-creek-001")
if __name__=="__main__":unittest.main()
