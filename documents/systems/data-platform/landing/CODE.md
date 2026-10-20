---
status: active
scope: landing-apps-source-map
last_verified: 2026-10-16
source_sha: d019429332e794e412426cf9c5053bafa043c05e
---

# Landing / Discovery / Claim — CODE / 源码导航

> 本页是该组件的**唯一源码地图**。基于上述 Git SHA 的源码和功能边界分类；不重复当前项目状态或运维 Runbook。组件概览见 [README.md](README.md)，运行安全门槛见 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。

## Landing Discovery 与 Claim/Fencing

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`batch_ledger.py`](../../../../local-data-platform/apps/landing_claim/batch_ledger.py) | PostgreSQL Claim 生命周期、身份与锁操作 |
| [`claim_discovered_inventory.py`](../../../../local-data-platform/apps/landing_claim/claim_discovered_inventory.py) | Discovery 到 Claim 的权限及 Allowlist Gate |
| [`lease_fence.py`](../../../../local-data-platform/apps/landing_claim/lease_fence.py) | 事务内 Claim Owner / Lease Fencing |
| [`verify_fencing_rollback.py`](../../../../local-data-platform/apps/landing_claim/verify_fencing_rollback.py) | 仅使用合成身份的 Fencing ROLLBACK 检验 |
| [`verify_rollback.py`](../../../../local-data-platform/apps/landing_claim/verify_rollback.py) | 合成 Claim 状态流转 ROLLBACK 检验 |
| [`run_airflow_scan.py`](../../../../local-data-platform/apps/landing_discovery/run_airflow_scan.py) | 供 Airflow KPO 使用的只读扫描入口与 XCom 摘要 |
| [`scan_ready_batches.py`](../../../../local-data-platform/apps/landing_discovery/scan_ready_batches.py) | 只读枚举与验证已发布 S3 READY Batch |

## 历史 Intake / Landing Resolver

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`resolve_verified_intake_file.py`](../../../../local-data-platform/apps/resolve_verified_intake_file.py) | 历史 TASK001 验证报告与源文件解析 |
| [`build_intake_manifest.py`](../../../../local-data-platform/apps/task001/build_intake_manifest.py) | 历史 Intake Manifest 文件构建 |
| [`landing_guard.py`](../../../../local-data-platform/apps/task001/landing_guard.py) | 历史 Landing Prefix / 写入路径防护 |
| [`resolve_verified_landing_file.py`](../../../../local-data-platform/apps/task004/resolve_verified_landing_file.py) | 历史 S3 Landing Manifest 和来源验证 |
| [`validate_new_only_v2_manifest.py`](../../../../local-data-platform/apps/task004/validate_new_only_v2_manifest.py) | NEW_ONLY v2 Manifest Reader 合同验证 |

## 历史 Encounter/Visit Raw 与 Processed 发布安全

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`build_encounter_raw_evidence.py`](../../../../local-data-platform/apps/task003/build_encounter_raw_evidence.py) | 历史 Encounter Raw 发布来源与结果证据 |
| [`build_visit_processed_dq.py`](../../../../local-data-platform/apps/task003/build_visit_processed_dq.py) | 历史 Processed Visit DQ 证据构建 |
| [`build_visit_processed_manifest.py`](../../../../local-data-platform/apps/task003/build_visit_processed_manifest.py) | 历史 Visit Processed APPROVED Manifest 构建 |
| [`build_visit_processed_runtime_bundle.py`](../../../../local-data-platform/apps/task003/build_visit_processed_runtime_bundle.py) | 历史 Visit Spark/ConfigMap 静态运行包构建 |
| [`build_visit_writer_reservation.py`](../../../../local-data-platform/apps/task003/build_visit_writer_reservation.py) | 历史 Visit 发布 Reservation 模板构建 |
| [`inspect_visit_processed_prefix.py`](../../../../local-data-platform/apps/task003/inspect_visit_processed_prefix.py) | 历史 Processed S3 Prefix 只读冲突检查 |
| [`issue_visit_processed_write_permit.py`](../../../../local-data-platform/apps/task003/issue_visit_processed_write_permit.py) | 历史单次写入 Permit 校验与签发 |
| [`plan_visit_processed.py`](../../../../local-data-platform/apps/task003/plan_visit_processed.py) | 历史不可变 Visit Processed 发布 Plan |
| [`prepare_visit_processed_write_intent.py`](../../../../local-data-platform/apps/task003/prepare_visit_processed_write_intent.py) | 历史发布写入意图；自身不授权写入 |
| [`prepare_visit_writer_bundle_inventory.py`](../../../../local-data-platform/apps/task003/prepare_visit_writer_bundle_inventory.py) | 历史 Visit Runtime Bundle 的源文件清单 |
| [`resolve_approved_encounter_raw.py`](../../../../local-data-platform/apps/task003/resolve_approved_encounter_raw.py) | 历史批准的 Encounter Raw 读取与证据解析 |
| [`resolve_encounter_raw_resume.py`](../../../../local-data-platform/apps/task003/resolve_encounter_raw_resume.py) | 历史中断 Encounter Raw 发布恢复校验 |
| [`verify_encounter_remote_metadata.py`](../../../../local-data-platform/apps/task003/verify_encounter_remote_metadata.py) | 历史远端 Encounter Manifest / DQ 元数据只读检查 |
| [`verify_visit_processed_plan.py`](../../../../local-data-platform/apps/task003/verify_visit_processed_plan.py) | 历史 Visit Processed Plan 与固定证据的比较 |

## 关联入口

[Discovery DAG](../../../../local-data-platform/airflow/dags/landing_batch_discovery.py) · [Discovery Tests](../../../../local-data-platform/tests/landing_discovery) · [Claim Tests](../../../../local-data-platform/tests/landing_claim) · [NEW_ONLY READY Policy](../../../../local-data-platform/contracts/synthea/new-only/ready-publication-policy-v1.json)

这里的历史 `task003` 文件负责 S3 Raw/Processed 发布安全、Intent、Reservation 与 DQ 证据，而不是已经独立实现的新增业务 ETL。Discover 不等于自动 Claim 或 COMMIT。

## Landing Claim / Writer Fence SQL

| 源文件 | 角色 / 安全边界 |
| --- | --- |
| [`create_landing_batch_ledger.sql`](../../../../local-data-platform/sql/landing_claim/create_landing_batch_ledger.sql) | DDL，需要授权：新建独立的 Landing Claim/Lease Ledger |
| [`writer_fence_v1_deploy.sql`](../../../../local-data-platform/sql/landing_claim/writer_fence_v1_deploy.sql) | DDL，需要授权：Writer 同一事务 Fence 函数及权限部署 |
| [`writer_fence_v1_rollback_proof.sql`](../../../../local-data-platform/sql/landing_claim/writer_fence_v1_rollback_proof.sql) | ROLLBACK-only 演练：验证 Fence/角色/事务协议；仍要审查执行环境 |

**执行区别**：Ledger/Fence Deploy 是能改变数据库 Schema 或权限的 DDL，绝不视为只读检查。Rollback-proof 虽在事务内回滚，也需要确认执行主体、对象状态和完整的审查与授权。Synthea READY 发布 Contract 属于 [Synthea CODE](../synthea/CODE.md)，Landing 只引用不复制权威协议。

## Landing 容器镜像与构建边界

| 源文件（直接链接） | 用途与运行边界 |
| --- | --- |
| [`Dockerfile`](../../../../local-data-platform/images/landing-claim-runtime/Dockerfile) | Landing Claim/Lease/Fencing 容器：复制 Claim Python，使用 psycopg/boto3；含 Claim 权限边界 |
| [`Dockerfile`](../../../../local-data-platform/images/landing-discovery-runtime/Dockerfile) | 只读 S3 READY Inventory 扫描容器：复制 Discovery、Resolver 和 v2 合同 |
| [`Dockerfile`](../../../../local-data-platform/images/landing-processing-runtime/Dockerfile) | 在历史 TASK004 控制镜像 Digest 上叠加 NEW_ONLY v2 Resolver/Contract；不授予 Claim/COMMIT |

**镜像兼容性**：`landing-processing-runtime` 继承固定 TASK004 控制面 Digest，只叠加新的 v2 Landing Resolver 与 JSON Contract；切勿因为 Builder 成功而假定运行中消费者已经升级，或把 `claim=disabled` 镜像等同于获得 Claim/Writer 权限。

## 历史 Shell / 脚本导航（由 landing 组件负责）

> 本清单是历史 Step Shell 的**代码索引，不是按顺序执行的 Runbook**。这些文件可能使用固定 Git SHA/Batch ID、操作 S3/PG/K8s、修改仓库源码或生成本地报告；任何执行须先读脚本全文并核对 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。新脚本必须按组件/能力命名，不能新增 `taskNNN` 路径。

## 历史 task001（5 个入口）

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`00-reset-task001.sh`](../../../../local-data-platform/scripts/task001/00-reset-task001.sh) | [HIGH / review] 历史 TASK001 reset 历史 Task 脚本；可能清理本地文件/临时资源，禁止无审查重放 |
| [`02-s3-readonly-preflight.sh`](../../../../local-data-platform/scripts/task001/02-s3-readonly-preflight.sh) | [CHECK / verify effects] 历史 TASK001 S3 readonly preflight 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`03-publish-landing-payload.sh`](../../../../local-data-platform/scripts/task001/03-publish-landing-payload.sh) | [EXECUTE / review] 历史 TASK001 publish landing payload 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`04-publish-intake-manifest.sh`](../../../../local-data-platform/scripts/task001/04-publish-intake-manifest.sh) | [EXECUTE / review] 历史 TASK001 publish intake manifest 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`05-validate-task001.sh`](../../../../local-data-platform/scripts/task001/05-validate-task001.sh) | [CHECK / verify effects] 历史 TASK001 validate 历史 Task 脚本 |

> **历史退役（2026-10-20）**：2026-10-20 退役：STEP05A-E 一次性验收冻结 Markdown 生成器，不是 Landing 工作负载。原始源码保留于 [`05-write-ae-freeze-doc.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b418c1e077be7db21d56f9131709f73fcb0b66b9/local-data-platform/scripts/task003/05-write-ae-freeze-doc.sh)（只读历史链接），并由独立 Healthcare-Specs 备份保存；这些链接不是当前可执行入口。

> **历史生成器退役（2026-10-20，Task 4.9 第五批）**：已从活动代码树退役五个固定旧 Task003 的 Plan Validation、Writer Bundle Inventory、Writer Observer、Processed DQ 和 Processed Manifest **源码生成/安装 Shell**。它们生成的 **13/13 正式 Python / Shell / Unit Test 内容逐字节与 Main 一致**，后者全部保留，不删除任何 DQ / Manifest 发布、Writer 观察或校验运行入口。恢复原生成器可使用固定历史 Git 版本：[`05g1-prepare-visit-processed-plan-validation.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/0177ee3b466215492254803d28dfa4de06eff244/local-data-platform/scripts/task003/05g1-prepare-visit-processed-plan-validation.sh)、[`05g2c2c2b1-prepare-bundle-inventory-source.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/0177ee3b466215492254803d28dfa4de06eff244/local-data-platform/scripts/task003/05g2c2c2b1-prepare-bundle-inventory-source.sh)、[`05g2c2c3d1-prepare-writer-observer.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/0177ee3b466215492254803d28dfa4de06eff244/local-data-platform/scripts/task003/05g2c2c3d1-prepare-writer-observer.sh)、[`05g3a-prepare-processed-dq-builder.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/0177ee3b466215492254803d28dfa4de06eff244/local-data-platform/scripts/task003/05g3a-prepare-processed-dq-builder.sh)、[`05g4a-prepare-processed-manifest-builder.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/0177ee3b466215492254803d28dfa4de06eff244/local-data-platform/scripts/task003/05g4a-prepare-processed-manifest-builder.sh)。保留的源码不意味着旧固定 Batch 可以安全重放。

> **历史源码安装器退役（2026-10-20，Task 4.9 第六批）**：移除 3 份已物化到正式 Git 源码的历史安装器；对应正式源码、Contract、运行脚本、单测 **8/8 全字节 MATCH** 且全部保留。原生成器可使用固定 Git 恢复地址：[`05g2a-prepare-visit-processed-prefix-guard.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/e3ce9f2e5adbfd22f25e3bfca1b2ae892f4f086a/local-data-platform/scripts/task003/05g2a-prepare-visit-processed-prefix-guard.sh)、[`05g2b-prepare-visit-processed-remote.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/e3ce9f2e5adbfd22f25e3bfca1b2ae892f4f086a/local-data-platform/scripts/task003/05g2b-prepare-visit-processed-remote.sh)、[`05g2c1-prepare-visit-processed-write-intent.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/e3ce9f2e5adbfd22f25e3bfca1b2ae892f4f086a/local-data-platform/scripts/task003/05g2c1-prepare-visit-processed-write-intent.sh)。不可将历史链接当作现行入口，也不自动重放旧 Batch。

> **历史源码安装器清理（2026-10-20，Task 4.9 第七批）**：从固定 Main `61d393b31bd68b92af98908e2934762131842242` 退役 6 个旧 Processed Runtime Bundle / Writer Reservation / Postlock / Permit / DQ Publisher / Reservation Release 生成安装器。生成的 **12/12 正式源文件与当时 Git 全字节 MATCH，全部保留**，活动 Shell 39→33。原文件的不可变恢复链接：[`05g2c2c2b2-prepare-runtime-bundle-source.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/61d393b31bd68b92af98908e2934762131842242/local-data-platform/scripts/task003/05g2c2c2b2-prepare-runtime-bundle-source.sh)、[`05g2c2c3a-prepare-writer-reservation-acquire.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/61d393b31bd68b92af98908e2934762131842242/local-data-platform/scripts/task003/05g2c2c3a-prepare-writer-reservation-acquire.sh)、[`05g2c2c3b-prepare-postlock-preflight.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/61d393b31bd68b92af98908e2934762131842242/local-data-platform/scripts/task003/05g2c2c3b-prepare-postlock-preflight.sh)、[`05g2c2c3c1-prepare-write-permit-source.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/61d393b31bd68b92af98908e2934762131842242/local-data-platform/scripts/task003/05g2c2c3c1-prepare-write-permit-source.sh)、[`05g3b1-prepare-processed-dq-publisher-source.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/61d393b31bd68b92af98908e2934762131842242/local-data-platform/scripts/task003/05g3b1-prepare-processed-dq-publisher-source.sh)、[`05g5a-prepare-processed-publication-reservation-release.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/61d393b31bd68b92af98908e2934762131842242/local-data-platform/scripts/task003/05g5a-prepare-processed-publication-reservation-release.sh)。特别保留 `05g4c1-prepare-processed-manifest-publisher-source.sh`：`05g4c2-prepare-processed-manifest-publication.sh` 与 `05g4c2-publish-processed-manifest.sh` 的 Git checkpoint guard 仍直接列举该文件，暂不能将其当作零依赖生成器。详情见 [Batch7 Evidence](../../../../openspec/changes/relocate-local-data-platform/evidence/LOCAL-DP-TASK003-BATCH7-SOURCE-INSTALLERS-20261020.md)。

## 历史 task003（33 个入口）

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`05d-prepare-visit-remote-metadata.sh`](../../../../local-data-platform/scripts/task003/05d-prepare-visit-remote-metadata.sh) | [PREPARE / may write] 历史 TASK003 prepare visit remote metadata 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05d-verify-visit-remote-metadata.sh`](../../../../local-data-platform/scripts/task003/05d-verify-visit-remote-metadata.sh) | [CHECK / verify effects] 历史 TASK003 verify visit remote metadata 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`05e-prepare-visit-raw.sh`](../../../../local-data-platform/scripts/task003/05e-prepare-visit-raw.sh) | [PREPARE / may write] 历史 TASK003 prepare visit raw 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05e-validate-visit-raw.sh`](../../../../local-data-platform/scripts/task003/05e-validate-visit-raw.sh) | [CHECK / verify effects] 历史 TASK003 validate visit raw 脚本 |
| [`05g1-plan-visit-processed.sh`](../../../../local-data-platform/scripts/task003/05g1-plan-visit-processed.sh) | [CHECK / verify effects] 历史 TASK003 plan visit processed 脚本 |
| [`05g1-prepare-visit-processed-plan.sh`](../../../../local-data-platform/scripts/task003/05g1-prepare-visit-processed-plan.sh) | [PREPARE / may write] 历史 TASK003 prepare visit processed plan 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05g1-verify-visit-processed-plan.sh`](../../../../local-data-platform/scripts/task003/05g1-verify-visit-processed-plan.sh) | [CHECK / verify effects] 历史 TASK003 verify visit processed plan 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`05g2a-inspect-visit-processed-prefix.sh`](../../../../local-data-platform/scripts/task003/05g2a-inspect-visit-processed-prefix.sh) | [CHECK / verify effects] 历史 TASK003 inspect visit processed prefix 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`05g2b-inspect-visit-processed-remote.sh`](../../../../local-data-platform/scripts/task003/05g2b-inspect-visit-processed-remote.sh) | [CHECK / verify effects] 历史 TASK003 inspect visit processed remote 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`05g2c1-verify-visit-processed-write-intent.sh`](../../../../local-data-platform/scripts/task003/05g2c1-verify-visit-processed-write-intent.sh) | [CHECK / verify effects] 历史 TASK003 verify visit processed write intent 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`05g2c2a-prepare-writer-reservation-source.sh`](../../../../local-data-platform/scripts/task003/05g2c2a-prepare-writer-reservation-source.sh) | [PREPARE / may write] 历史 TASK003 prepare writer reservation source 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05g2c2a-prepare-writer-reservation.sh`](../../../../local-data-platform/scripts/task003/05g2c2a-prepare-writer-reservation.sh) | [PREPARE / may write] 历史 TASK003 prepare writer reservation 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05g2c2c2a-check-runtime-readonly.sh`](../../../../local-data-platform/scripts/task003/05g2c2c2a-check-runtime-readonly.sh) | [CHECK / verify effects] 历史 TASK003 check runtime readonly 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`05g2c2c2a-prepare-runtime-readonly.sh`](../../../../local-data-platform/scripts/task003/05g2c2c2a-prepare-runtime-readonly.sh) | [PREPARE / may write] 历史 TASK003 prepare runtime readonly 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05g2c2c2a-repair-rbac-command.sh`](../../../../local-data-platform/scripts/task003/05g2c2c2a-repair-rbac-command.sh) | [HIGH / review] 历史 TASK003 repair rbac command 脚本；会修改历史脚本源码，不能作为只读检查 |
| [`05g2c2c2b1-prepare-bundle-inventory.sh`](../../../../local-data-platform/scripts/task003/05g2c2c2b1-prepare-bundle-inventory.sh) | [PREPARE / may write] 历史 TASK003 prepare bundle inventory 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05g2c2c2b2-prepare-runtime-bundle.sh`](../../../../local-data-platform/scripts/task003/05g2c2c2b2-prepare-runtime-bundle.sh) | [PREPARE / may write] 历史 TASK003 prepare runtime bundle 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05g2c2c3a-acquire-writer-reservation.sh`](../../../../local-data-platform/scripts/task003/05g2c2c3a-acquire-writer-reservation.sh) | [EXECUTE / review] 历史 TASK003 acquire writer reservation 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`05g2c2c3b-capture-postlock-preflight.sh`](../../../../local-data-platform/scripts/task003/05g2c2c3b-capture-postlock-preflight.sh) | [PREPARE / may write] 历史 TASK003 capture postlock preflight 脚本 |
| [`05g2c2c3c-issue-write-permit.sh`](../../../../local-data-platform/scripts/task003/05g2c2c3c-issue-write-permit.sh) | [EXECUTE / review] 历史 TASK003 issue write permit 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`05g2c2c3c2-launch-visit-processed-writer.sh`](../../../../local-data-platform/scripts/task003/05g2c2c3c2-launch-visit-processed-writer.sh) | [EXECUTE / review] 历史 TASK003 launch visit processed writer 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`05g2c2c3c2-prepare-atomic-writer-launcher.sh`](../../../../local-data-platform/scripts/task003/05g2c2c3c2-prepare-atomic-writer-launcher.sh) | [PREPARE / may write] 历史 TASK003 prepare atomic writer launcher 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05g2c2c3d1-observe-visit-processed-writer.sh`](../../../../local-data-platform/scripts/task003/05g2c2c3d1-observe-visit-processed-writer.sh) | [CHECK / verify effects] 历史 TASK003 observe visit processed writer 脚本 |
| [`05g2c2c3d2b2-prepare-independent-readback.sh`](../../../../local-data-platform/scripts/task003/05g2c2c3d2b2-prepare-independent-readback.sh) | [PREPARE / may write] 历史 TASK003 prepare independent readback 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05g2c2c3d2b2-run-independent-readback.sh`](../../../../local-data-platform/scripts/task003/05g2c2c3d2b2-run-independent-readback.sh) | [EXECUTE / review] 历史 TASK003 run independent readback 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`05g3a-build-processed-dq.sh`](../../../../local-data-platform/scripts/task003/05g3a-build-processed-dq.sh) | [PREPARE / may write] 历史 TASK003 build processed dq 脚本 |
| [`05g3b2-prepare-processed-dq-publication.sh`](../../../../local-data-platform/scripts/task003/05g3b2-prepare-processed-dq-publication.sh) | [PREPARE / may write] 历史 TASK003 prepare processed dq publication 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05g3b2-publish-processed-dq.sh`](../../../../local-data-platform/scripts/task003/05g3b2-publish-processed-dq.sh) | [EXECUTE / review] 历史 TASK003 publish processed dq 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`05g4a-build-processed-manifest.sh`](../../../../local-data-platform/scripts/task003/05g4a-build-processed-manifest.sh) | [PREPARE / may write] 历史 TASK003 build processed manifest 脚本 |
| [`05g4c1-prepare-processed-manifest-publisher-source.sh`](../../../../local-data-platform/scripts/task003/05g4c1-prepare-processed-manifest-publisher-source.sh) | **[E/HOLD — active Git checkpoint guards]** [PREPARE / may write] 历史 TASK003 prepare processed manifest publisher source 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05g4c2-prepare-processed-manifest-publication.sh`](../../../../local-data-platform/scripts/task003/05g4c2-prepare-processed-manifest-publication.sh) | [PREPARE / may write] 历史 TASK003 prepare processed manifest publication 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05g4c2-publish-processed-manifest.sh`](../../../../local-data-platform/scripts/task003/05g4c2-publish-processed-manifest.sh) | [EXECUTE / review] 历史 TASK003 publish processed manifest 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`05g5a-release-processed-publication-reservation.sh`](../../../../local-data-platform/scripts/task003/05g5a-release-processed-publication-reservation.sh) | [HIGH / review] 历史 TASK003 release processed publication reservation 脚本 |

## 历史 task004（2 个入口）

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`05a-prepare-generic-landing-resolver.sh`](../../../../local-data-platform/scripts/task004/05a-prepare-generic-landing-resolver.sh) | [PREPARE / may write] 历史 TASK004 prepare generic landing resolver 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05c-resolve-runtime-lineage.sh`](../../../../local-data-platform/scripts/task004/05c-resolve-runtime-lineage.sh) | [LEGACY / review] 历史 TASK004 resolve runtime lineage 脚本 |

## 源码维护约定

**新增、删除、重命名或移动本组件负责的 `apps/`、`contracts/`、`sql/`、`images/`、`kubernetes/` 或 `scripts/` 源文件，必须在同一个 PR 更新本 CODE.md。** CODE.md 只做导航，不能当作重新执行历史脚本的授权。历史 `taskNNN` 程序仍可能被 Docker COPY、Import 或冻结 Contract 引用；先看 [Legacy 重构计划](../../../engineering/development/LEGACY-CODE-REFACTOR-PLAN.md)。

