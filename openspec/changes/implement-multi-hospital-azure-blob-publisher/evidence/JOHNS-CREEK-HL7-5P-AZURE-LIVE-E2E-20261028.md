# Johns Creek Hospital B — real NEW 5-person FHIR → OIE → HL7 ADT^A01 → Azure Blob E2E

**Status: LIVE_E2E_ACCEPTED (hospital B only).** Verified against actual Kubernetes/OIE/Azure operations; not inferred from CI or old Channel PoC. The existing Atlanta Hospital A direct FHIR → Azure E2E was already separately proven in runs [#40238053772](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40238053772) and [#40250606505](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40250606505).

## Immutable evidence

| Evidence | Actual value |
| --- | --- |
| Self-Runner full live E2E Run | [#40715594941](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40715594941), **SUCCESS**, first attempt |
| Reusable parameterized workflow | `.github/workflows/azure-blob-johns-creek-hl7-e2e-manual.yml`, Self-Runner Main after PR [#332](https://github.com/JohnZhang-DataForge/Self-Runner/pull/332) |
| Reviewed one-time input dispatch | [#40715541150](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40715541150), **SUCCESS**; dispatched `hospital_profile=johns-creek-hl7`, `population=5` |
| New source request ID | `johnscreek-hl7-gh-40715594941` |
| Hospital / Feed | `johns-creek-hospital-b` / `johns-creek-hospital-b-hl7-v2` |
| Healthcare source pinned SHA | `55e8023c3521cb80a2c0ec3574fce7a3f05d6b91` |
| Publisher pinned immutable GHCR Digest | `ghcr.io/johnzhang-dataforge/healthcare-azure-blob-publisher@sha256:735c9914d7e413a78ed29b221a54b98c3af08ab43c1178fab8432ee633475361` |
| Source generation manifest SHA256 | `3f997d301a92457985b8aaa7945cf6367935f701cda41265d72de1cc4cedf229` |
| Azure landing manifest SHA256 | `5ee8b78f5307bdeedfcdde76b2d9b15289ce6a2ea5242baddfc34d9f8219f193` |
| Azure landing manifest ETag | `"0x8DF3507BA545A58"` |

## Observed pipeline results

1. **Producer:** `JOHNS_CREEK_GENERATOR_NEW_FHIR=PASS`. A unique new GitHub Run ID produced a fresh 5-patient Synthea FHIR source on the existing worker01 Generator PVC, with immutable source request + Manifest.
2. **Source audit:** `NEW_JOHNS_CREEK_SOURCE_AUDIT=PASS`: **136 Encounter** resources, of which **6 inpatient (IMP)**. Source bytes and full count matched the verified Manifest *before any OIE POST*.
3. **OIE transformation:** `OIE_PERSISTED_MESSAGES_NEW_ACK_RECEIPTS=136`: 136 new Message ID receipts from the already-running, verified Johns Creek Channel; the historical 32 prior PoC messages were **not reused**. The existing OIE Channel Deployment was not changed by this E2E. The Channel's separate config/STARTED live proof is [#40677753788](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40677753788).
4. **HL7 classification:** **6** inpatient Encounters yielded ADT^A01 HL7 v2 artifacts; **130** non-inpatient Encounters were explicitly skipped, never fabricated into admissions. This is the important semantic difference between *encounter count*, *OIE message receipt count* and *published Azure HL7 object count*.
5. **Azure independent verification:** `AZURE_HL7_INDEPENDENT_OBJECT_GET_SHA_ETAG=6` and `AZURE_HL7_INDEPENDENT_MANIFEST_GET_SHA_ETAG=PASS`; after the actual immutable commit the Runner independently GET/HEAD-checked each object SHA256, size, metadata, Content-Type and ETag, plus manifest SHA256/ETag and the 6+130=136 reconciliation.
6. **Idempotency:** `SAME_HL7_REQUEST_BLOB_IMMUTABLE_IDEMPOTENT=PASS` on a **Publisher-only** repeat/remote readback. There was **no second submission of 136 messages to OIE**.
7. **Cleanup and ownership:** `JOHNS_CREEK_RUN_SCOPED_EPHEMERAL_CLEANUP=PASS`. Only unique run-owned Kubernetes temporary resources were removed; no source PVC, OIE Derby, previous messages or committed Azure objects were deleted. `SEAWEEDFS_PG_OMOP_FABRIC_WRITES=NO`.

GitHub job logs record `JOHNS_CREEK_HL7_AZURE_LANDING_E2E=PASS` and the above identities. This is a **real landing acceptance** for Hospital B, not a claim that downstream Fabric Notebook/Pipeline ingestion or OMOP transformation has run. Hospital A's independent prior acceptance plus this Hospital B Run complete the *two separate hospital landing paths* in the current scope.

## Failure history and scope boundaries

- Previous **100-person** Johns Creek [Run #40684333118](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40684333118) failed *after Generator, before any confirmed OIE POST*. Read-only [#40687243910](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40687243910) established audit Job exit 1/BackoffLimitExceeded, and read-only [#40687643277](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40687643277) located the frozen FHIR Encounter count rejection in `oie_message_submit.py`. Its original failing state remains intact; it was not retried or counted as successful. The 5-person Run used a **different, new request ID**.
- The **reusable** Workflow now accepts `hospital_profile`, `population` (5 or 10, default 5), optional `seed`, optional `reference_date`, with confirmation `PUBLISH_SYNTHETIC_HL7`. Data and request ID are built by the Generator/Profile contract, **not embedded in the Workflow**. See Self-Runner PR [#332](https://github.com/JohnZhang-DataForge/Self-Runner/pull/332). Currently deployed OIE Channel/assigning authority is explicitly Johns Creek; the parameterized workflow does **not** imply every arbitrary Profile has a deployed HL7 Channel.
- Internal-only OIE admin permission and SHA256-pinned server leaf TLS are a consciously approved MVP compatibility compromise. They are **not** a native RBAC least-privilege identity or general publicly exposed OIE endpoint. No Gateway, keystore rotation or OIE Derby migration occurred in this acceptance.
- OIDC short-lived token lifecycle, Terraform RBAC IaC proof, credential rotation, downstream Fabric/OMOP and public demo remain separate, **not accepted** by these landing results. Do not close unrelated OpenSpec tasks based on this run.

**Acceptance classification:** `SOURCE_GENERATOR_LIVE_PASS / VERIFIED_FHIR_ENCOUNTERS_136 / OIE_FRESH_ACKS_136 / HL7_ADT_A01_6 / NON_INPATIENT_SKIP_130 / AZURE_BLOB_AND_MANIFEST_INDEPENDENT_READBACK_PASS / PUBLISHER_ONLY_IDEMPOTENT_PASS / RUN_SCOPED_CLEANUP_PASS`.
