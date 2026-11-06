"""Offline-only OIE Channel V2 build gates; no OIE REST/K8s calls."""
from __future__ import annotations

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "local-data-platform"))
from apps.clinical_producers.oie.build_adt_events_v2_channel import (
    CHANNEL_ID, CHANNEL_NAME, render_channel_v2
)
from apps.clinical_producers.oie.build_channel import CHANNEL_ID as OLD_CHANNEL_ID


class ChannelV2Tests(unittest.TestCase):
    def test_new_channel_never_reuses_deployed_a01_id(self):
        self.assertNotEqual(CHANNEL_ID, OLD_CHANNEL_ID)
        self.assertLessEqual(len(CHANNEL_NAME), 40)
        xml = ET.fromstring(render_channel_v2())
        self.assertEqual(xml.findtext("id"), CHANNEL_ID)
        self.assertEqual(xml.findtext("name"), CHANNEL_NAME)

    def test_unchanged_restricted_internal_channel_reader(self):
        xml = ET.fromstring(render_channel_v2())
        self.assertEqual(xml.findtext("sourceConnector/transportName"), "Channel Reader")
        self.assertEqual(
            xml.find("sourceConnector/properties").get("class"),
            "com.mirth.connect.connectors.vm.VmReceiverProperties"
        )
        self.assertEqual(xml.findtext("properties/initialState"), "STARTED")
        self.assertIn("fhirToHl7AdtEventsV2", xml.findtext("preprocessingScript"))
        self.assertIn("input.requested_event_type", xml.findtext("preprocessingScript"))
        self.assertIn("OIE_ADT_V2_EVENT_NOT_APPLICABLE", xml.findtext("preprocessingScript"))
        self.assertNotIn("localhost:8333", render_channel_v2())
        self.assertNotIn("https://", xml.findtext("preprocessingScript"))

    def test_same_source_inputs_produce_byte_stable_channel_xml(self):
        first, second = render_channel_v2(), render_channel_v2()
        self.assertEqual(first, second)

    def test_old_legacy_deployment_id_not_present_in_new_xml(self):
        self.assertNotIn(OLD_CHANNEL_ID, render_channel_v2())


if __name__ == "__main__":
    unittest.main()
