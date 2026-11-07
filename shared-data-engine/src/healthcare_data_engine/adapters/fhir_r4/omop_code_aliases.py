"""FHIR R4 source vocabulary aliases to *existing LocalDP semantic keys*.

This is source-specific lexical normalization, NOT an OMOP Concept mapping.
The Shared G5 OMOP Mapper and the platform-specific Writers do not own
FHIR/HL7/CSV input syntax. No Concept IDs, clinical defaults or runtime I/O.
The prospective semantic equivalence of each alias still needs reviewer approval.
"""
from __future__ import annotations

# These are semantic keys already defined by the immutable LocalDP contracts.
# Do not add 1002-5 as "hawaiian", nor coerce UNK to an invented Race ID.
FHIR_R4_LOCALDP_ALIASES: dict[str, dict[str, str]] = {
    "gender_code": {"male": "M", "female": "F"},
    "race_code": {
        "2028-9": "asian",
        "2054-5": "black",
        "2106-3": "white",
        "2076-8": "hawaiian",
    },
    "ethnicity_code": {"2135-2": "hispanic", "2186-5": "nonhispanic"},
    "encounter_class": {
        kind: kind for kind in (
            "ambulatory", "emergency", "home", "hospice", "inpatient",
            "outpatient", "snf", "urgentcare", "virtual", "wellness",
        )
    },
}

# FHIR source *meaning*, not a target OMOP Concept ID and not signoff.
# Human reviewers must decide what to do for the source code and for
# OMOP "no race information" before Gold publication.
FHIR_R4_RACE_REVIEW_HINTS: dict[str, str] = {
    "1002-5": "AMERICAN_INDIAN_OR_ALASKA_NATIVE",
    "UNK": "HL7_NULLFLAVOR_UNKNOWN",
}
