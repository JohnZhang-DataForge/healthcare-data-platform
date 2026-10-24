# Azure Blob Publisher — dedicated namespace (static)

## Target runtime boundary

- **Publisher namespace:** `dw-az-blob` (NOT `dw-synthea`).
- **Generator and frozen PVC:** `dw-synthea/synthea-new-generator-state`, resident on `worker01`; **never** reference this existing PVC directly from a `dw-az-blob` Pod. A Kubernetes PVC claim is namespace-scoped, even when access is read-only.
- **OIE:** `dw-oie/oie-debug` and its Retain PVC stay unchanged; persisted messages are read by a scoped, authenticated future fetcher, not by mounting Derby.
- **No new PVC, HostPath, PV rebind, NodePort, LoadBalancer, namespace-wide Kubernetes token or storage credentials** are authorized in this static step.
- Azure Storage Account/Container/RBAC and any `dw-az-blob` identity Secret remain **unconfigured and unverified**; these YAML files do not create them.

## Source-to-publisher handoff still to implement

1. A separately authorized source-side read operation in `dw-synthea` verifies the frozen new Generator Request/FHIR Manifest and bytes using `source_handoff.verify_handoff()`; it mounts its existing PVC read-only on `worker01`. It does not regenerate data.
2. A bounded, integrity-checked, authenticated handoff must transfer precisely those verified immutable inputs to **ephemeral** Publisher input storage within `dw-az-blob`. The transport (e.g. a tightly scoped Runner-managed Job-to-Job stream) requires its own review, implementation and tests. **Not yet implemented.** Never hardcode worker host paths or pretend cross-namespace PVC mounts work.
3. For the Johns Creek route, an independently authenticated OIE readback must furnish the new Request's Channel/Message IDs and exact HL7 bytes / skip receipts before invoking `oie_hl7_publisher`. Do not replay the previously accepted 32 Derby messages.
4. A separate Publisher runtime Job/image in `dw-az-blob` will consume the staged input and scoped `dw-az-blob` Secret. It may PUT to the approved existing Azure Landing Container only after Azure preflight and action-level authorization. Manifest must be verified by real GET **last**.

## Manifest deployment scope and safety

- `namespace.yaml` declares ONLY the Namespace and Pod Security **restricted** labels.
- `networkpolicy-default-deny.yaml` is **independent** and is NOT to be applied blindly. If applied, all ingress and egress are blocked, including DNS/OIE/Azure; approved DNS and narrowly scoped OIE/Azure egress allow rules must be designed and tested before publisher traffic can flow. NetworkPolicy enforcement depends on cluster CNI.
- A read-only cluster preflight must check the actual `dw-az-blob` namespace/UID, existing jobs/pods and controls, worker01/OIE/Generator PVC, current SHA, queued/running Self-Runner operations, and authorization before **any** `kubectl create/apply`. A namespace already present with mismatching ownership must HOLD rather than relabeling/adopting it.
- Never commit or echo Azure SP client secrets, SAS tokens or OIE credentials; do not create secrets until their scope and delivery process are approved.
- A successful GitHub PR/hosted static test is **NOT** evidence that `dw-az-blob` exists in Kubernetes.

References: [Safe Operations](../../../../documents/engineering/operations/SAFE-OPERATIONS.md), [Session Coordination](../../../../documents/engineering/development/SESSION-COORDINATION.md), [active Publisher OpenSpec](../../../../openspec/changes/implement-multi-hospital-azure-blob-publisher/tasks.md).
