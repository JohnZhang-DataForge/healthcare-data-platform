# Johns Creek Hospital B — NEW 50-person FHIR → OIE → HL7 → Azure Blob E2E

**Acceptance: REAL_LIVE_E2E_PASS.** This is an additional, independent synthetic batch, not a replay of previously validated 5-person Run #40715594941 or failed 100-person Run #40684333118.

## Actual main-branch workflow evidence

| Item | Actual observed value |
| --- | --- |
| Reusable parameterized E2E | [Self-Runner Run #40731892374](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40731892374) — both GitHub-hosted preflight and real `dw-runner-set` publication jobs SUCCESS |
| One-shot parameter invocation | [Self-Runner Run #40731847060](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40731847060) — GitHub API `workflow_dispatch` accepted after checking previous unique runs |
| Requested input | `hospital_profile=johns-creek-hl7`, `population=50`; optional `seed` and `reference_date` left to Profile defaults |
| New source request | `johnscreek-hl7-gh-40731892374` |
| Hospital and feed | `johns-creek-hospital-b` / `johns-creek-hospital-b-hl7-v2` |
| Pinned Healthcare main source | `875d5e93ee49df66bd26eee097c9c96a609f7ce3` (PR #548, sender event limit increased to 5,000) |
| Immutable GHCR Publisher image | `ghcr.io/johnzhang-dataforge/healthcare-azure-blob-publisher@sha256:ba8dbf51347f05f58db9af0e5777a125df571ab67644bad7d7fb7f0b15857ead` |
| Main GHCR push verification | [Healthcare Run #40731253810](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40731253810), SHA-only package pushed and pulled from registry |
| Source Manifest SHA256 | `a0d81382b2075bfe4164d867bf7dd823dd32d4384181782f4d0b8b5e0e312317` |
| Azure Landing Manifest SHA256 | `d7d234181e6af05f871c07c5eb04931d5baef85b317a87e6e8df7da98a64de23` |
| Azure Landing Manifest ETag | `"0x8DF3515A1EE1C78"` |

## Real data flow counts and checks

1. **Generator:** `SYNTHETIC_HL7_POPULATION=50` and `JOHNS_CREEK_GENERATOR_NEW_FHIR=PASS` for a fresh, run-ID-specific FHIR source. The reusable Workflow accepts a population parameter; no patient records or fixed batch payloads are embedded in the Workflow.
2. **Full source audit:** `NEW_JOHNS_CREEK_SOURCE_AUDIT=PASS` and `NEW_SOURCE_ENCOUNTERS=1941`, with **21 inpatient** encounters. Full frozen source Manifest SHA and source count verified before ANY OIE message POST. The former 1,000-event rejection was raised to a still-bounded 5,000 across both Producer and Runner; no previous requests were resubmitted.
3. **OIE 4.7 message ingestion:** `OIE_PERSISTED_MESSAGES_NEW_ACK_RECEIPTS=1941`, bound to this same new run and actual source SHA. The verified existing Johns Creek Channel was used; `OIE_CHANNEL_DEPLOYMENT_CHANGED=NO`. The older 32 historic OIE messages and accepted 5-person Run were not replayed.
4. **Clinical classification:** **21** inpatient Encounters yielded actual HL7 ADT^A01 artifacts and **1,920** non-inpatient encounters were explicitly SKIPPED. The OIE message count is not the Azure HL7 object count by design.
5. **Immutable Azure delivery:** `AZURE_HL7_INDEPENDENT_OBJECT_GET_SHA_ETAG=21` and `AZURE_HL7_INDEPENDENT_MANIFEST_GET_SHA_ETAG=PASS` proved actual independent remote Blob GET/HEAD/SHA/ETag for all 21 HL7 objects and the final Landing Manifest after first commit.
6. **Idempotency:** `SAME_HL7_REQUEST_BLOB_IMMUTABLE_IDEMPOTENT=PASS` after **Publisher-only** repeat with independent remote byte/ETag reconciliation; there was no second OIE POST of the 1,941 Encounter messages.
7. **Cleanup and isolation:** `JOHNS_CREEK_RUN_SCOPED_EPHEMERAL_CLEANUP=PASS` and `SEAWEEDFS_PG_OMOP_FABRIC_WRITES=NO`. Only new run-owned temporary Kubernetes Jobs/ConfigMaps were cleaned; frozen Synthea source, OIE Derby and committed Azure records remain persisted.

The real Runner output ended in `JOHNS_CREEK_HL7_AZURE_LANDING_E2E=PASS`. This verifies **Landing**, not Fabric Notebook/Pipeline, OneLake silver/gold models or OMOP transforms. Atlanta Hospital A direct FHIR and previous Johns Creek 5-person HL7 E2E remain independently accepted, not overwritten by this new cohort.

## Scope and future runs

- The reusable Workflow accepts `hospital_profile`, `population` (5, 10 or 50), optional `seed`, optional `reference_date`. The default test remains **5**; 50 is opt-in, not a fixed input in reusable code.
- The current deployed HL7 Channel/Assigning Authority corresponds to **Johns Creek**. Choosing an unrelated hospital Profile does not magically configure OIE for it.
- No automatic retry of unknown/partial OIE POST is permitted. Only Publisher-only, byte-identical immutable Azure idempotency is safely verified.
- Existing internal OIE admin+exact TLS leaf pin is an expressly approved internal MVP compromise, not a native RBAC model or public OIE endpoint.
- This incremental 50-person run provides extra scale evidence for the existing 3.2/3.3/4.2 landing acceptance; the independent governance tasks and Fabric/OMOP workloads are still unproven by this Run.
