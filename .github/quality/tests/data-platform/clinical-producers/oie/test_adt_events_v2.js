"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "../../../../../../");
const IMPL = path.join(ROOT, "local-data-platform/apps/clinical_producers/oie/adt_events_v2.js");
const mapper = require(IMPL).fhirToHl7AdtEventsV2;
const cfg = {
  hospital_id: "johns-creek-hospital-b",
  feed_id: "johns-creek-hospital-b-hl7-v2",
  request_id: "synthetic-new-source-001",
  assigning_authority: "JOHNSCREEKB"
};
const SYSTEM = "urn:oid:2.16.840.1.113883.6.238";
function patient() {
  return {
    resourceType: "Patient",
    id: "patient-one",
    name: [{family: "Cooper", given: ["Anne"]}],
    birthDate: "1980-01-01", gender: "female",
    extension: [
      {url: "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
        extension: [{url: "ombCategory", valueCoding: {system: SYSTEM, code: "2106-3", display: "White"}}]},
      {url: "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
        extension: [{url: "ombCategory", valueCoding: {system: SYSTEM, code: "2186-5", display: "Not Hispanic or Latino"}}]}
    ]
  };
}
function encounter(status="finished", cls="IMP") {
  const enc = {
    resourceType: "Encounter", id: "visit-one", status,
    class: {system: "http://terminology.hl7.org/CodeSystem/v3-ActCode", code: cls},
    subject: {reference: "urn:uuid:source-patient-one"},
    period: {start: "2026-11-05T07:00:00-05:00"}
  };
  if (status === "finished") enc.period.end = "2026-11-06T05:00:00-05:00";
  return enc;
}
function bundle(status="finished", cls="IMP") {
  return {
    resourceType: "Bundle", type: "collection",
    entry: [
      {fullUrl: "urn:uuid:source-patient-one", resource: patient()},
      {resource: encounter(status, cls)}
    ]
  };
}
function segment(raw, name) {
  const line = raw.split("\r").find(x => x.startsWith(name+"|"));
  assert.ok(line, "missing "+name);
  return line.split("|");
}

test("finished IMP has one A01 and one A03, each a full valid v2.5.1 event", () => {
  const r = mapper(bundle(), cfg);
  assert.equal(r.schema_version, "oie-adt-events-v2");
  assert.equal(r.status, "MAPPING_VERIFIED_ONLY");
  assert.deepEqual(r.messages.map(x => x.event_type), ["A01", "A03"]);
  assert.notEqual(r.messages[0].control_id, r.messages[1].control_id);
  for (const x of r.messages) {
    const msh = segment(x.hl7, "MSH"), evn = segment(x.hl7, "EVN");
    const pid = segment(x.hl7, "PID"), pv1 = segment(x.hl7, "PV1");
    assert.equal(msh[8], "ADT^"+x.event_type+"^ADT_"+x.event_type);
    assert.equal(msh[11], "2.5.1");
    assert.equal(evn[1], x.event_type);
    assert.equal(msh[9], x.control_id);
    assert.equal(pid[3], "patient-one^^^JOHNSCREEKB^MR");
    assert.equal(pid[5], "Cooper^Anne");
    assert.equal(pid[7], "19800101");
    assert.equal(pid[8], "F");
    assert.equal(pid[10], "2106-3^White^CDCREC");
    assert.equal(pid[22], "2186-5^Not Hispanic or Latino^CDCREC");
    assert.equal(pv1[2], "I");
    assert.equal(pv1[19], "visit-one^^^JOHNSCREEKB^VN");
    assert.equal(pv1[44], "20261105120000+0000");
    assert.ok(x.hl7.endsWith("\r"));
    if (x.event_type === "A03") {
      assert.equal(pv1[45], "20261106100000+0000");
      assert.equal(msh[6], "20261106100000+0000");
    } else {
      assert.equal(pv1[45], "");
      assert.equal(msh[6], "20261105120000+0000");
    }
  }
});
test("in-progress IMP creates A01 only; never invents discharge A03", () => {
  const r = mapper(bundle("in-progress"), cfg);
  assert.deepEqual(r.messages.map(x => x.event_type), ["A01"]);
  assert.equal(segment(r.messages[0].hl7, "PV1")[45], "");
});
test("non-IMP/planned/cancelled does not become admission", () => {
  for(const c of ["AMB","EMER","OBSENC"]){
    assert.equal(mapper(bundle("finished",c),cfg).messages.length,0);
  }
  for(const status of ["planned","cancelled"]){
    assert.equal(mapper(bundle(status),cfg).messages.length,0);
  }
});
test("missing real birthDate / race / ethnicity / gender FAIL CLOSED", () => {
  let b=bundle(); delete b.entry[0].resource.birthDate;
  assert.throws(()=>mapper(b,cfg),/PATIENT_BIRTH_DATE_REQUIRED/);
  b=bundle(); b.entry[0].resource.birthDate="2026-02-30";
  assert.throws(()=>mapper(b,cfg),/PATIENT_BIRTH_DATE_INVALID/);
  b=bundle(); b.entry[0].resource.extension.shift();
  assert.throws(()=>mapper(b,cfg),/RACE_EXTENSION_REQUIRED/);
  b=bundle(); b.entry[0].resource.extension.pop();
  assert.throws(()=>mapper(b,cfg),/ETHNICITY_EXTENSION_REQUIRED/);
  b=bundle(); b.entry[0].resource.gender="unknown";
  assert.throws(()=>mapper(b,cfg),/GENDER_MAPPING_PROFILE/);
});
test("unknown, ambiguous or incorrect coding systems are refused", () => {
  let b=bundle(); b.entry[0].resource.extension[0].extension[0].valueCoding.code="9999-9";
  assert.throws(()=>mapper(b,cfg),/RACE_MAPPING_PROFILE/);
  b=bundle(); b.entry[0].resource.extension[0].extension[0].valueCoding.system="NOT_CDCREC";
  assert.throws(()=>mapper(b,cfg),/RACE_MAPPING_PROFILE/);
  b=bundle(); b.entry[0].resource.extension[0].extension.push(
    {url:"ombCategory",valueCoding:{system:SYSTEM,code:"2028-9"}}
  );
  assert.throws(()=>mapper(b,cfg),/RACE_MAPPING_PROFILE/);
});
test("finished missing end, wrong period and malformed start are blocked", () => {
  let b=bundle(); delete b.entry[1].resource.period.end;
  assert.throws(()=>mapper(b,cfg),/ENCOUNTER_END_MISSING/);
  b=bundle(); b.entry[1].resource.period.end="2026-11-04T09:00:00-05:00";
  assert.throws(()=>mapper(b,cfg),/ENCOUNTER_END_BEFORE_START/);
  b=bundle(); b.entry[1].resource.period.start="not-a-date";
  assert.throws(()=>mapper(b,cfg),/ENCOUNTER_START_INVALID/);
});
test("subject mismatch and duplicate encounter must HOLD", () => {
  let b=bundle(); b.entry[1].resource.subject.reference="Patient/does-not-exist";
  assert.throws(()=>mapper(b,cfg),/PATIENT_REFERENCE/);
  b=bundle(); b.entry.push(JSON.parse(JSON.stringify(b.entry[1])));
  assert.throws(()=>mapper(b,cfg),/ENCOUNTER_ID/);
});
test("byte-for-byte replay determinism; same identifiers are isolated by hospital", () => {
  const one=mapper(bundle(),cfg);
  assert.deepEqual(one,mapper(bundle(),cfg));
  const another=mapper(bundle(),{...cfg,hospital_id:"atlanta-hospital"});
  assert.notEqual(one.messages[0].control_id,another.messages[0].control_id);
});
test("HL7 escape sequence integrity and CR-injection prevention", () => {
  let b=bundle();
  b.entry[0].resource.name=[{family:"A|B",given:["C^D&Z"]}];
  const p=segment(mapper(b,cfg).messages[0].hl7,"PID");
  assert.equal(p[5],"A\\F\\B^C\\S\\D\\T\\Z");
  b=bundle(); b.entry[0].resource.name=[{family:"A\rOBX|1",given:["Jane"]}];
  assert.throws(()=>mapper(b,cfg),/CONTROL_CHARACTER_IN_FIELD/);
});
test("OIE Rhino-like VM without Node globals loads the ES5 mapping script", () => {
  const source=fs.readFileSync(IMPL,"utf8");
  const ctx={}; vm.runInNewContext(source,ctx);
  assert.equal(typeof ctx.fhirToHl7AdtEventsV2,"function");
  assert.equal(ctx.fhirToHl7AdtEventsV2(bundle(),cfg).messages.length,2);
});
