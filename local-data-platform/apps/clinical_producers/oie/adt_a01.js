/*
 * OIE Code Template candidate: strict, deterministic FHIR R4 -> HL7 2.5.1 ADT^A01.
 * ES5-compatible JavaScript; deliberately independent of Node/OIE globals.
 * Runtime OIE Channel wiring and parse-back are separate verification gates.
 */
(function (root) {
    "use strict";

    function blocked(reason) { throw new Error("OIE_ADT_BLOCKED_" + reason); }
    function validId(value) {
        return typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9.-]{0,79}$/.test(value);
    }
    function cleanConfig(config) {
        if (!config || typeof config !== "object") blocked("CONFIG");
        var keys = ["hospital_id", "feed_id", "request_id", "assigning_authority"];
        for (var i = 0; i < keys.length; i++) {
            if (!validId(config[keys[i]])) blocked("CONFIG_ID");
        }
        return config;
    }
    function escaped(value) {
        var map = {"\\": "\\E\\", "|": "\\F\\", "^": "\\S\\", "~": "\\R\\", "&": "\\T\\"};
        return String(value == null ? "" : value).replace(/[\\|^~&]/g, function (m) { return map[m]; });
    }
    function hl7Time(value) {
        if (typeof value !== "string" || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value)) {
            blocked("ADMISSION_TIME");
        }
        var d = new Date(value);
        if (isNaN(d.getTime())) blocked("ADMISSION_TIME");
        // UTC-normalized: source offset is retained only through the represented instant.
        var iso = d.toISOString();
        return iso.slice(0, 4) + iso.slice(5, 7) + iso.slice(8, 10) +
            iso.slice(11, 13) + iso.slice(14, 16) + iso.slice(17, 19) + "+0000";
    }
    function subjectIndex(entries) {
        var patients = {};
        for (var i = 0; i < entries.length; i++) {
            var ent = entries[i], p = ent && ent.resource;
            if (p && p.resourceType === "Patient") {
                if (!validId(p.id)) blocked("PATIENT_ID");
                var refs = ["Patient/" + p.id];
                if (typeof ent.fullUrl === "string" && ent.fullUrl.length) refs.push(ent.fullUrl);
                for (var j = 0; j < refs.length; j++) {
                    if (patients[refs[j]]) blocked("PATIENT_DUPLICATE");
                    patients[refs[j]] = p;
                }
            }
        }
        return patients;
    }
    function encode(patient, enc, cfg, timestamp) {
        var ref = cfg.hospital_id + "-" + cfg.feed_id + "-" + cfg.request_id +
            "-" + enc.id + "-A01";
        if (ref.length > 199) blocked("CONTROL_ID_TOO_LONG");
        var authority = escaped(cfg.assigning_authority);
        var patientId = escaped(patient.id);
        var encounterId = escaped(enc.id);
        var human = patient.name && patient.name[0] || {};
        var family = escaped(human.family || "UNKNOWN");
        var given = escaped(human.given && human.given[0] || "UNKNOWN");
        var msh = ["MSH", "^~\\&", "SYNTHEA_SIM", authority,
                   "LANDING", "SYNTHETIC", timestamp, "",
                   "ADT^A01^ADT_A01", escaped(ref), "P", "2.5.1"];
        var evn = ["EVN", "A01", timestamp];
        var pid = ["PID", "1", "", patientId + "^^^" + authority + "^MR",
                   "", family + "^" + given];
        var pv1 = ["PV1", "1", "I"];
        while (pv1.length <= 44) pv1.push("");
        pv1[19] = encounterId + "^^^" + authority + "^VN";
        pv1[44] = timestamp;
        return [msh.join("|"), evn.join("|"), pid.join("|"), pv1.join("|")].join("\r") + "\r";
    }
    function fhirToAdtA01(bundle, config) {
        var cfg = cleanConfig(config);
        if (!bundle || bundle.resourceType !== "Bundle" || !Array.isArray(bundle.entry)) {
            blocked("FHIR_BUNDLE");
        }
        var entries = bundle.entry, patients = subjectIndex(entries);
        var seen = {}, rows = [], skipped = 0;
        for (var i = 0; i < entries.length; i++) {
            var enc = entries[i] && entries[i].resource;
            if (!enc || enc.resourceType !== "Encounter") continue;
            if (!validId(enc.id) || seen[enc.id]) blocked("ENCOUNTER_ID");
            seen[enc.id] = true;
            var cls = enc["class"] || {};
            if (cls.system !== "http://terminology.hl7.org/CodeSystem/v3-ActCode" ||
                cls.code !== "IMP" ||
                (enc.status !== "in-progress" && enc.status !== "finished")) {
                skipped++;
                continue;
            }
            var ref = enc.subject && enc.subject.reference;
            var patient = typeof ref === "string" && patients[ref];
            if (!patient) blocked("PATIENT_REFERENCE");
            if (!enc.period || !enc.period.start) blocked("ADMISSION_START_MISSING");
            var admission = hl7Time(enc.period.start);
            rows.push({event_id: cfg.request_id + ":" + enc.id + ":A01",
                       encounter_id: enc.id, patient_id: patient.id,
                       hl7: encode(patient, enc, cfg, admission)});
        }
        rows.sort(function (a, b) {
            return a.event_id < b.event_id ? -1 : (a.event_id > b.event_id ? 1 : 0);
        });
        return {schema_version: "oie-adt-a01-mapping-v1",
                status: "MAPPING_VERIFIED_ONLY",
                messages: rows, skipped_non_admissions: skipped};
    }
    root.fhirToAdtA01 = fhirToAdtA01;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = {fhirToAdtA01: fhirToAdtA01};
    }
}(this));
