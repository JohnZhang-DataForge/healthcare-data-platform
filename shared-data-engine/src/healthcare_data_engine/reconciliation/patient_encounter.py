"""Pure final Canonical Patient/Encounter PK/FK/source-batch reconciliation."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from healthcare_data_engine.models.batch_context import BatchContext
from healthcare_data_engine.quality.result import Finding, TransformResult


@dataclass(frozen=True)
class PatientEncounterReconciliation:
    patient: TransformResult
    encounter: TransformResult

    @property
    def metrics(self) -> dict[str, int]:
        return {
            "patient_accepted": len(self.patient.accepted),
            "encounter_accepted": len(self.encounter.accepted),
            "patient_rejected": len(self.patient.rejected),
            "encounter_rejected": len(self.encounter.rejected),
            "patient_quarantined": len(self.patient.quarantined),
            "encounter_quarantined": len(self.encounter.quarantined),
        }


def reconcile_patient_encounter(patient: TransformResult, encounter: TransformResult,
                                context: BatchContext) -> PatientEncounterReconciliation:
    """Fail closed: only accepted, context-consistent Patient keys can back Encounters.

    This transforms in-memory results only. Caller separately validates and
    independently reads back physical Silver Delta tables before approval.
    """
    expected_system = context.namespaced_source_system
    expected_batch = context.source_batch_id
    p_count = Counter((r.get("source_system"), r.get("source_record_id"))
                      for r in patient.accepted)
    e_count = Counter((r.get("source_system"), r.get("source_encounter_id"))
                      for r in encounter.accepted)
    patient_ok, patient_bad, encounter_ok, encounter_bad = [], list(patient.rejected), [], list(encounter.rejected)

    for row in patient.accepted:
        key = (row.get("source_system"), row.get("source_record_id"))
        reason = None
        if row.get("source_system") != expected_system or row.get("source_batch_id") != expected_batch:
            reason = "PATIENT_SOURCE_NAMESPACE_CONFLICT"
        elif p_count[key] != 1:
            reason = "PATIENT_DUPLICATE_PRIMARY_KEY"
        if reason:
            patient_bad.append(Finding("REJECTED", reason, "canonical patient PK/batch scope",
                                       "Patient", str(row.get("source_record_id")),
                                       str(row.get("source_file"))))
        else:
            patient_ok.append(row)

    accepted_patient_ids = {row["source_record_id"] for row in patient_ok}
    for row in encounter.accepted:
        key = (row.get("source_system"), row.get("source_encounter_id"))
        reason = None
        if row.get("source_system") != expected_system or row.get("source_batch_id") != expected_batch:
            reason = "ENCOUNTER_SOURCE_NAMESPACE_CONFLICT"
        elif e_count[key] != 1:
            reason = "ENCOUNTER_DUPLICATE_PRIMARY_KEY"
        elif row.get("source_person_id") not in accepted_patient_ids:
            reason = "ENCOUNTER_PATIENT_NOT_ACCEPTED"
        if reason:
            encounter_bad.append(Finding("REJECTED", reason, "canonical Encounter FK/PK/batch scope",
                                         "Encounter", str(row.get("source_encounter_id")),
                                         str(row.get("source_file"))))
        else:
            encounter_ok.append(row)

    return PatientEncounterReconciliation(
        patient=TransformResult(tuple(patient_ok), patient.quarantined, tuple(patient_bad)),
        encounter=TransformResult(tuple(encounter_ok), encounter.quarantined, tuple(encounter_bad)))
