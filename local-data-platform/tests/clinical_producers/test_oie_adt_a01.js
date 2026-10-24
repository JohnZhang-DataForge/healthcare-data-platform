"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const {fhirToAdtA01} = require("../../apps/clinical_producers/oie/adt_a01.js");

const config = {
  hospital_id:"demo-johns-creek", feed_id:"demo-johns-creek-hl7-v2",
  request_id:"johnscreek-fhir-0001", assigning_authority:"DEMOJC"
};
function bundle(klass="IMP", status="finished") {
  return {resourceType:"Bundle",type:"collection",entry:[
    {fullUrl:"urn:uuid:patient-one",resource:{resourceType:"Patient",id:"patient-one",
      name:[{family:"Cooper",given:["Anne"]}]}},
    {resource:{resourceType:"Encounter",id:"enc-one",status,
      class:{system:"http://terminology.hl7.org/CodeSystem/v3-ActCode",code:klass},
      subject:{reference:"urn:uuid:patient-one"},
      period:{start:"2026-10-24T09:15:30-04:00"}}}
  ]};
}
function fields(s,segment) {
  return s.split("\r").find(x=>x.startsWith(segment+"|")).split("|");
}
test("strict real A01 segment structure with patient, encounter, historic timestamp",()=>{
  const result=fhirToAdtA01(bundle(),config);
  assert.equal(result.messages.length,1);
  assert.equal(result.status,"MAPPING_VERIFIED_ONLY");
  const s=result.messages[0].hl7;
  const msh=fields(s,"MSH"), evn=fields(s,"EVN"), pid=fields(s,"PID"), pv1=fields(s,"PV1");
  assert.equal(msh[8],"ADT^A01^ADT_A01");
  assert.equal(msh[11],"2.5.1");
  assert.equal(evn[1],"A01");
  assert.equal(msh[6],"20261024131530+0000");
  assert.match(msh[9],/demo-johns-creek.*enc-one-A01$/);
  assert.equal(pid[3],"patient-one^^^DEMOJC^MR");
  assert.equal(pid[5],"Cooper^Anne");
  assert.equal(pv1[2],"I");
  assert.equal(pv1[19],"enc-one^^^DEMOJC^VN");
  assert.equal(pv1[44],"20261024131530+0000");
});
test("same request and event yields identical MSH-10 / whole byte payload",()=>{
  assert.deepEqual(fhirToAdtA01(bundle(),config),fhirToAdtA01(bundle(),config));
});
test("hospital and feed scope control ID",()=>{
  const a=fields(fhirToAdtA01(bundle(),config).messages[0].hl7,"MSH")[9];
  const b=fields(fhirToAdtA01(bundle(),{...config,hospital_id:"demo-other-hospital"}).messages[0].hl7,"MSH")[9];
  assert.notEqual(a,b);
});
test("AMB/EMER/OBSENC never become A01",()=>{
  for(const cls of ["AMB","EMER","OBSENC"]) {
    const result=fhirToAdtA01(bundle(cls),config);
    assert.equal(result.messages.length,0);
    assert.equal(result.skipped_non_admissions,1);
  }
});
test("planned and cancelled IMP never become A01",()=>{
  for(const status of ["planned","cancelled"]) {
    assert.equal(fhirToAdtA01(bundle("IMP",status),config).messages.length,0);
  }
});
test("missing start or patient reference blocks",()=>{
  let b=bundle(); delete b.entry[1].resource.period;
  assert.throws(()=>fhirToAdtA01(b,config),/ADMISSION_START_MISSING/);
  b=bundle();b.entry[1].resource.subject.reference="Patient/unknown";
  assert.throws(()=>fhirToAdtA01(b,config),/PATIENT_REFERENCE/);
});
test("invalid timestamp and duplicate encounter ID block",()=>{
  let b=bundle();b.entry[1].resource.period.start="not-a-date";
  assert.throws(()=>fhirToAdtA01(b,config),/ADMISSION_TIME/);
  b=bundle();b.entry.push(JSON.parse(JSON.stringify(b.entry[1])));
  assert.throws(()=>fhirToAdtA01(b,config),/ENCOUNTER_ID/);
});
test("HL7 delimiter escaping of patient name",()=>{
  const b=bundle();
  b.entry[0].resource.name=[{family:"A|B",given:["C^D&Z"]}];
  const pid=fields(fhirToAdtA01(b,config).messages[0].hl7,"PID");
  assert.equal(pid[5],"A\\F\\B^C\\S\\D\\T\\Z");
});
test("empty or non-Bundle input rejects",()=>{
  assert.throws(()=>fhirToAdtA01({},config),/FHIR_BUNDLE/);
  assert.throws(()=>fhirToAdtA01(null,config),/FHIR_BUNDLE/);
});
test("ES5 script loads without require or Node globals (OIE-like script context)",()=>{
  const src=fs.readFileSync(path.join(__dirname,"../../apps/clinical_producers/oie/adt_a01.js"),"utf8");
  const ctx={}; vm.runInNewContext(src,ctx);
  assert.equal(typeof ctx.fhirToAdtA01,"function");
  assert.equal(ctx.fhirToAdtA01(bundle(),config).messages.length,1);
});
