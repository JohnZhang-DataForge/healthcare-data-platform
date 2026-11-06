"""Build a NEW versioned OIE 4.7.0 Channel from its known upstream fixture.

No live OIE calls. Preserves deployed A01 Channel ID, Derby and PVC.
The channel processes one explicitly requested HL7 event per inbound source
message. Clinical eligibility is verified inside the OIE mapping function.
"""
from __future__ import annotations

import argparse
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

from apps.clinical_producers.oie.build_channel import UPSTREAM

SOURCE_ROOT = Path(__file__).resolve().parent
MAPPING = SOURCE_ROOT / "adt_events_v2.js"
CHANNEL_ID = str(uuid.uuid5(
    uuid.NAMESPACE_URL,
    "healthcare-data-platform://oie/johns-creek-hl7-adt-events-v2",
))
CHANNEL_NAME = "Johns Creek HL7 ADT Events V2"

WRAPPER = """
// OIE 4.7.0/Rhino script, REST Channel Reader, EXACTLY ONE event per message.
// The sender requests A01 or A03 but MUST NOT decide clinical eligibility.
var input = JSON.parse(String(message));
if (!input || !input.bundle || typeof input.request_id !== "string" ||
    (input.requested_event_type !== "A01" && input.requested_event_type !== "A03")) {
    throw new Error("OIE_ADT_V2_BLOCKED_EVENT_ENVELOPE");
}
var result = fhirToHl7AdtEventsV2(input.bundle, {
    hospital_id: "johns-creek-hospital-b",
    feed_id: "johns-creek-hospital-b-hl7-v2",
    request_id: input.request_id,
    assigning_authority: "JOHNSCREEKB"
});
var selected = null;
for (var i = 0; i < result.messages.length; i++) {
    if (result.messages[i].event_type === input.requested_event_type) {
        if (selected !== null) {
            throw new Error("OIE_ADT_V2_BLOCKED_MULTIPLE_EVENTS");
        }
        selected = result.messages[i].hl7;
    }
}
if (selected === null) {
    return "OIE_ADT_V2_EVENT_NOT_APPLICABLE";
}
return selected;
"""


def render_channel_v2() -> str:
    fixture = UPSTREAM.read_text(encoding="utf-8")
    root = ET.fromstring(fixture)
    old_id = "62af393b-ff61-47ec-b5fa-ccd2cd08ce55"
    if root.tag != "channel" or root.findtext("name") != "Noop":
        raise ValueError("OIE_UPSTREAM_SHAPE_CHANGED")
    if root.findtext("id") != old_id:
        raise ValueError("OIE_UPSTREAM_ID_CHANGED")
    if root.find("sourceConnector/properties").get("class") != \
            "com.mirth.connect.connectors.vm.VmReceiverProperties":
        raise ValueError("OIE_UPSTREAM_RECEIVER_CHANGED")
    old_script = root.findtext("preprocessingScript")
    if not old_script or not old_script.startswith("// Modify the message"):
        raise ValueError("OIE_UPSTREAM_SCRIPT_CHANGED")
    old_fragment = "<preprocessingScript>" + escape(old_script) + "</preprocessingScript>"
    if fixture.count(old_fragment) != 1:
        raise ValueError("OIE_UPSTREAM_SCRIPT_FRAGMENT_AMBIGUOUS")
    script = MAPPING.read_text(encoding="utf-8") + "\n" + WRAPPER
    result = fixture.replace("<id>" + old_id + "</id>",
                             "<id>" + CHANNEL_ID + "</id>", 1)
    result = result.replace("<name>Noop</name>",
                            "<name>" + CHANNEL_NAME + "</name>", 1)
    result = result.replace(old_fragment,
                            "<preprocessingScript>" + escape(script) + "</preprocessingScript>", 1)
    xml = ET.fromstring(result)
    if (xml.findtext("id") != CHANNEL_ID or xml.findtext("name") != CHANNEL_NAME):
        raise ValueError("OIE_CHANNEL_V2_REWRITE_FAILED")
    if xml.findtext("preprocessingScript") != script:
        raise ValueError("OIE_CHANNEL_V2_SCRIPT_MISMATCH")
    if xml.findtext("destinationConnectors/connector/name") is not None:
        # Keep the upstream no-op writer as-is for static evaluation.
        pass
    assert len(CHANNEL_NAME) <= 40
    assert xml.findtext("sourceConnector/transportName") == "Channel Reader"
    assert "requested_event_type" in script
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    output = render_channel_v2()
    if args.output.exists():
        if args.output.read_text(encoding="utf-8") != output:
            raise SystemExit("OIE_ADT_V2_OUTPUT_EXISTS_WITH_DIFFERENT_BYTES")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
