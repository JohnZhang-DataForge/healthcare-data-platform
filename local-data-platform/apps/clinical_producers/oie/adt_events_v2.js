/*
 * Versioned, offline-first FHIR R4 -> HL7 v2.5.1 ADT^A01 / ADT^A03 source mapper.
 * ES5 safe for OIE 4.7.0 Rhino (no Node/global imports). Strict synthetic
 * hospital Pilot Profile: US Core ombCategory race/ethnicity, male/female sex.
 * This is NOT the already deployed A01 Channel. No file/Blob/Derby I/O.
 */
(function (root) {
    "use strict";

    var RACE_URI = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race";
    var ETHNICITY_URI = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity";
    var CDCREC_URI = "urn:oid:2.16.840.1.113883.6.238";
    var RACE_CODES = {
        "1002-5": "American Indian or Alaska Native",
        "2028-9": "Asian",
        "2054-5": "Black or African American",
        "2076-8": "Native Hawaiian or Other Pacific Islander",
        "2106-3": "White"
    };
    var ETHNICITY_CODES = {
        "2135-2": "Hispanic or Latino",
        "2186-5": "Not Hispanic or Latino"
    };

    function blocked(code) { throw new Error("OIE_ADT_V2_BLOCKED_" + code); }
    function validId(x) {
        return typeof x === "string" && /^[A-Za-z0-9][A-Za-z0-9.-]{0,79}$/.test(x);
    }
    function configScope(c) {
        var keys = ["hospital_id", "feed_id", "request_id", "assigning_authority"];
        if (!c || typeof c !== "object") blocked("CONFIG_MISSING");
        for (var i = 0; i < keys.length; i++) {
            if (!validId(c[keys[i]])) blocked("INVALID_CONFIG_ID");
        }
        return c;
    }
    function escapeHL7(value) {
        var text = value == null ? "" : String(value);
        if (/[\u0000-\u001f\u007f]/.test(text)) blocked("CONTROL_CHARACTER_IN_FIELD");
        var map = {"\\": "\\E\\", "|": "\\F\\", "^": "\\S\\",
                   "~": "\\R\\", "&": "\\T\\"};
        return text.replace(/[\\|^~&]/g, function (match) {return map[match];});
    }
    function fhirInstant(value, reason) {
        if (typeof value !== "string" ||
            !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value)) {
            blocked(reason);
        }
        var d = new Date(value);
        if (isNaN(d.getTime())) blocked(reason);
        var iso = d.toISOString();
        return {millis: d.getTime(),
                hl7: iso.slice(0, 4) + iso.slice(5, 7) + iso.slice(8, 10) +
                     iso.slice(11, 13) + iso.slice(14, 16) + iso.slice(17, 19) + "+0000"};
    }
    function birthDate(value) {
        if (typeof value !== "string" || !/^\d{4}-\d\d-\d\d$/.test(value)) {
            blocked("PATIENT_BIRTH_DATE_REQUIRED");
        }
        var d = new Date(value + "T00:00:00Z");
        if (isNaN(d.getTime()) || d.toISOString().slice(0, 10) !== value) {
            blocked("PATIENT_BIRTH_DATE_INVALID");
        }
        return value.replace(/-/g, "");
    }
    function demographicCode(patient, uri, allowed, name) {
        var extensions = patient.extension || [];
        if (!Array.isArray(extensions)) blocked(name + "_EXTENSION_SHAPE");
        var outer = null, count = 0;
        for (var i = 0; i < extensions.length; i++) {
            if (extensions[i] && extensions[i].url === uri) {
                outer = extensions[i]; count++;
            }
        }
        if (count !== 1 || !Array.isArray(outer.extension)) blocked(name + "_EXTENSION_REQUIRED");
        var value = null, seen = 0;
        for (var j = 0; j < outer.extension.length; j++) {
            var entry = outer.extension[j];
            if (entry && entry.url === "ombCategory") {
                value = entry.valueCoding; seen++;
            }
        }
        if (seen !== 1 || !value || value.system !== CDCREC_URI ||
            !Object.prototype.hasOwnProperty.call(allowed, value.code)) {
            blocked(name + "_MAPPING_PROFILE");
        }
        return value.code + "^" + escapeHL7(allowed[value.code]) + "^CDCREC";
    }
    function genderCode(gender) {
        // Pilot approved map intentionally limits the first deployment to unambiguous M/F.
        if (gender === "male") return "M";
        if (gender === "female") return "F";
        blocked("GENDER_MAPPING_PROFILE");
    }
    function patientByReference(entries) {
        var result = {};
        for (var i = 0; i < entries.length; i++) {
            var entry = entries[i], p = entry && entry.resource;
            if (p && p.resourceType === "Patient") {
                if (!validId(p.id)) blocked("PATIENT_ID");
                var refs = ["Patient/" + p.id];
                if (typeof entry.fullUrl === "string" && entry.fullUrl) refs.push(entry.fullUrl);
                for (var j = 0; j < refs.length; j++) {
                    if (Object.prototype.hasOwnProperty.call(result, refs[j])) blocked("DUPLICATE_PATIENT");
                    result[refs[j]] = p;
                }
            }
        }
        return result;
    }
    function patientFacts(patient) {
        var names = patient.name || [];
        var human = Array.isArray(names) && names.length ? names[0] : {};
        return {
            patient_id: patient.id,
            name: escapeHL7(human.family || "") + "^" +
                  escapeHL7(human.given && human.given[0] || ""),
            dob: birthDate(patient.birthDate),
            gender: genderCode(patient.gender),
            race: demographicCode(patient, RACE_URI, RACE_CODES, "RACE"),
            ethnicity: demographicCode(patient, ETHNICITY_URI, ETHNICITY_CODES, "ETHNICITY")
        };
    }
    function eventControlId(cfg, visitId, kind) {
        var ref = [cfg.hospital_id, cfg.feed_id, cfg.request_id, visitId, kind].join("-");
        if (ref.length > 199) blocked("CONTROL_ID_TOO_LONG");
        return escapeHL7(ref);
    }
    function encodeEvent(facts, encounter, cfg, start, eventTime, kind, end) {
        var authority = escapeHL7(cfg.assigning_authority);
        var pid = ["PID", "1", "", escapeHL7(facts.patient_id) + "^^^" + authority + "^MR",
                   "", facts.name];
        while (pid.length <= 22) pid.push("");
        pid[7] = facts.dob;
        pid[8] = facts.gender;
        pid[10] = facts.race;
        pid[22] = facts.ethnicity;

        var pv1 = ["PV1", "1", "I"];
        while (pv1.length <= 45) pv1.push("");
        pv1[19] = escapeHL7(encounter.id) + "^^^" + authority + "^VN";
        pv1[44] = start.hl7;
        if (kind === "A03") pv1[45] = end.hl7;

        var msh = ["MSH", "^~\\&", "SYNTHEA_SIM", authority, "LANDING", "SYNTHETIC",
                   eventTime.hl7, "", "ADT^" + kind + "^ADT_" + kind,
                   eventControlId(cfg, encounter.id, kind), "P", "2.5.1"];
        var evn = ["EVN", kind, eventTime.hl7];
        return [msh.join("|"), evn.join("|"), pid.join("|"), pv1.join("|")].join("\r") + "\r";
    }
    function fhirToHl7AdtEventsV2(bundle, config) {
        var cfg = configScope(config);
        if (!bundle || bundle.resourceType !== "Bundle" || !Array.isArray(bundle.entry)) {
            blocked("FHIR_BUNDLE");
        }
        var entries = bundle.entry, patients = patientByReference(entries);
        var seen = {}, messages = [], skipped = 0;
        for (var i = 0; i < entries.length; i++) {
            var enc = entries[i] && entries[i].resource;
            if (!enc || enc.resourceType !== "Encounter") continue;
            if (!validId(enc.id) || Object.prototype.hasOwnProperty.call(seen, enc.id)) {
                blocked("ENCOUNTER_ID");
            }
            seen[enc.id] = true;
            var cls = enc["class"] || {};
            if (cls.system !== "http://terminology.hl7.org/CodeSystem/v3-ActCode" ||
                cls.code !== "IMP" ||
                (enc.status !== "in-progress" && enc.status !== "finished")) {
                skipped++; continue;
            }
            var ref = enc.subject && enc.subject.reference;
            if (typeof ref !== "string" ||
                !Object.prototype.hasOwnProperty.call(patients, ref)) {
                blocked("PATIENT_REFERENCE");
            }
            var facts = patientFacts(patients[ref]);
            if (!enc.period || !enc.period.start) blocked("ENCOUNTER_START_MISSING");
            var start = fhirInstant(enc.period.start, "ENCOUNTER_START_INVALID");
            var end = null;
            if (enc.status === "finished") {
                if (!enc.period.end) blocked("ENCOUNTER_END_MISSING");
                end = fhirInstant(enc.period.end, "ENCOUNTER_END_INVALID");
                if (end.millis < start.millis) blocked("ENCOUNTER_END_BEFORE_START");
            }
            messages.push({
                event_type: "A01", event_id: cfg.request_id + ":" + enc.id + ":A01",
                patient_id: facts.patient_id, encounter_id: enc.id,
                control_id: eventControlId(cfg, enc.id, "A01"),
                hl7: encodeEvent(facts, enc, cfg, start, start, "A01", null)
            });
            if (end) {
                messages.push({
                    event_type: "A03", event_id: cfg.request_id + ":" + enc.id + ":A03",
                    patient_id: facts.patient_id, encounter_id: enc.id,
                    control_id: eventControlId(cfg, enc.id, "A03"),
                    hl7: encodeEvent(facts, enc, cfg, start, end, "A03", end)
                });
            }
        }
        messages.sort(function (a, b) {
            return a.event_id < b.event_id ? -1 : (a.event_id > b.event_id ? 1 : 0);
        });
        return {
            schema_version: "oie-adt-events-v2",
            status: "MAPPING_VERIFIED_ONLY",
            messages: messages,
            skipped_non_admissions: skipped
        };
    }
    root.fhirToHl7AdtEventsV2 = fhirToHl7AdtEventsV2;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = {fhirToHl7AdtEventsV2: fhirToHl7AdtEventsV2};
    }
}(this));
