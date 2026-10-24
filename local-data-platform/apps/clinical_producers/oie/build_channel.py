"""Render a narrowly scoped OIE 4.7 Channel from its upstream test fixture.

The upstream v4.7.0 repository ships this exact Channel Reader + Channel
Writer XML (XML declares compatible version 4.5.2). We replace only its
identity and preprocessingScript, preserving OIE XStream defaults.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

CHANNEL_ID = "69ace705-a675-45f6-b126-a3b22a65212a"
CHANNEL_NAME = "Johns Creek FHIR to HL7 ADT"
SKIP_MARKER = "OIE_ADT_NON_INPATIENT_SKIPPED"
SOURCE_ROOT = Path(__file__).resolve().parent
UPSTREAM = SOURCE_ROOT / "upstream-raw-reader.xml"
MAPPING = SOURCE_ROOT / "adt_a01.js"

WRAPPER = """
// OIE 4.7.0 / Rhino preprocessingScript receives Java String `message`.
// Transport sends one Patient+Encounter FHIR mini-Bundle per OIE message.
// The original validated Generator Bundle and manifest remain unchanged.
var input = JSON.parse(String(message));
if (!input || !input.bundle || typeof input.request_id !== "string") {
    throw new Error("OIE_ADT_BLOCKED_EVENT_ENVELOPE");
}
var result = fhirToAdtA01(input.bundle, {
    hospital_id: "demo-johns-creek",
    feed_id: "demo-johns-creek-hl7-v2",
    request_id: input.request_id,
    assigning_authority: "DEMOJC"
});
if (result.messages.length > 1) {
    throw new Error("OIE_ADT_BLOCKED_MULTIPLE_ENCOUNTERS_IN_ONE_EVENT");
}
if (result.messages.length === 0) {
    return "OIE_ADT_NON_INPATIENT_SKIPPED";
}
return result.messages[0].hl7;
"""

def render_channel() -> str:
    fixture = UPSTREAM.read_text(encoding="utf-8")
    mapping = MAPPING.read_text(encoding="utf-8")
    # Ensure a known-vetted upstream shape, not an arbitrary replacement.
    root = ET.fromstring(fixture)
    assert root.tag == "channel"
    assert root.findtext("name") == "Noop"
    assert root.findtext("id") == "62af393b-ff61-47ec-b5fa-ccd2cd08ce55"
    assert root.find("sourceConnector/properties").get("class") == "com.mirth.connect.connectors.vm.VmReceiverProperties"
    assert root.findtext("sourceConnector/transformer/inboundDataType") == "RAW"
    assert root.findtext("sourceConnector/transformer/outboundDataType") == "RAW"
    assert fixture.count("<id>62af393b-ff61-47ec-b5fa-ccd2cd08ce55</id>") == 1
    assert fixture.count("<name>Noop</name>") == 1
    original = root.findtext("preprocessingScript")
    assert original and original.startswith("// Modify the message")
    assert fixture.count("<preprocessingScript>") == 1
    assert fixture.count("</preprocessingScript>") == 1
    # Preserve fixture class properties/version; XML entity-escape only script.
    result = (fixture
        .replace("<id>62af393b-ff61-47ec-b5fa-ccd2cd08ce55</id>",
                 "<id>" + CHANNEL_ID + "</id>", 1)
        .replace("<name>Noop</name>", "<name>" + CHANNEL_NAME + "</name>", 1)
        .replace("<preprocessingScript>" + escape(original) + "</preprocessingScript>",
                 "<preprocessingScript>" + escape(mapping + "\n" + WRAPPER) + "</preprocessingScript>", 1)
    )
    root2 = ET.fromstring(result)
    assert root2.findtext("id") == CHANNEL_ID
    assert root2.findtext("name") == CHANNEL_NAME
    script = root2.findtext("preprocessingScript")
    assert "fhirToAdtA01" in script and "OIE_ADT_NON_INPATIENT_SKIPPED" in script
    assert root2.find("sourceConnector/properties").get("class") == "com.mirth.connect.connectors.vm.VmReceiverProperties"
    assert root2.findtext("properties/initialState") == "STARTED"
    return result

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Do not write to an existing output unless it's exactly the same bytes.
    xml = render_channel()
    if args.output.exists():
        if args.output.read_text(encoding="utf-8") != xml:
            raise SystemExit("OIE_CHANNEL_OUTPUT_ALREADY_EXISTS_DIFFERENT")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(xml, encoding="utf-8")

if __name__ == "__main__":
    main()
