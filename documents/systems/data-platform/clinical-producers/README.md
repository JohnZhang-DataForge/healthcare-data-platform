# Clinical Producers — OIE / FHIR → HL7

本组件负责独立医院来源的 FHIR Bundle 入口与 OIE 4.7.0 的 HL7 ADT 转换验证。与 Synthea 的合成数据生成不同，OIE Channel、镜像和 K8s 按独立医院/Feed、版本和 Secret 审核，不直接接管 Synthea PVC 或其他 OMOP Writer。

## Browse by responsibility

| Need | Human document | Actual source owner |
| --- | --- | --- |
| FHIR Encounter → ADT A01 Channel mapping | [OIE ADT mapping](OIE-ADT-MAPPING.md) | [Clinical Producer JS](../../../../local-data-platform/apps/clinical_producers/oie/adt_a01.js) |
| Exact OIE 4.7.0 upstream image | [OIE image build](OIE-IMAGE-BUILD.md) | [Image workflow](../../../../.github/workflows/oie-470-isolated-image-smoke.yml) |
| K8s Namespace / Secret / StatefulSet candidates | [OIE templates](OIE-K8S-TEMPLATES.md) | [Kubernetes manifests](../../../../local-data-platform/kubernetes/manifests/oie/) |
| Disposable historical startup | [Debug phase](OIE-DEBUG-HISTORY.md) | [Debug deployment template](../../../../local-data-platform/kubernetes/manifests/oie/debug/) |
| Durable retained PVC and acceptance | [Persistent phase](OIE-PERSISTENT-HISTORY.md) | [Persistent YAML](../../../../local-data-platform/kubernetes/manifests/oie/persistent/) |

**Source map ownership:** the current trusted Local DP source CODE checker registers clinical Producer/OIE source rows in [Synthea CODE](../synthea/CODE.md) due historical multi-source ownership. That CODE map remains the **single** source inventory until its trusted policy is deliberately upgraded; this README is a human-facing OIE component navigator, **not** a duplicated CODE map. Reorganizing the documentation does not automatically authorize OIE Channel import, Kubernetes mutation or new HL7/Blob delivery. See [OIE Active OpenSpec](../../../../openspec/changes/implement-oie-fhir-to-hl7-adt-poc/tasks.md).
