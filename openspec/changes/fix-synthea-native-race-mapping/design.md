# Design

## Context

当前真实调用链：`new_only_airflow_writer.execute → joint_s3_rollback.s3_rows → task004_cdm_dynamic_source.read → task004_cdm_dynamic_adapters.transform → BLOCKED=unknown_demographic`。失败发生于 SQL COMMIT 之前，不能以此证明业务映射成功或修改了 PostgreSQL。原始失败批次已在 [Run #39525509790](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39525509790) 做过诊断。

真实 **旧/新镜像、原始 S3 Parquet、只读、无数据库连接** A/B：
- [Run #39534932448](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39534932448)：早晨已成功 `synthea-new-only-gh-39421910846`，16 Person、4,259 Visit；旧/新 Writer 两次映射 PASS，Person/Visit 输出 SHA 完全一致。
- [Run #39535834807](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39535834807)：失败 `synthea-new-only-gh-39524542198`，64 Person、12,446 Visit；旧/新 Writer 均报 `unknown_demographic`。Gender 为 F44/M20、Ethnicity 为 nonhispanic61/hispanic3，均受现有映射支持；Race 为 white36、black23、asian2、hawaiian2、**native1**，唯一不受支持的是 `native`。两种镜像中输入 SHA、分布及失败结果完全一致。
- 旧镜像固定 `@sha256:1565a4481669520916a336e7ce5de52f3856333c43632078d03854b22bc28ae4`；新镜像固定 `@sha256:f7904a5a5dd86c288bd369c7daddb8cb3d21c315c3e68e80ea2fe43dcd1c864f`，均有实际 Pod `imageID`。

## Decision

1. **先确认编码语义**：核实 Synthea v3.3.0 的 `native` 实际源编码含义、OMOP 标准词表版本/相关 Concept ID 是否有效。将来源和 ID 记录在修复 PR；不在设计中无证据指定数字，不用默认 0 隐藏可映射的合法类别。
2. **最小修复 Mapper**：保留已支持 Gender、Race、Ethnicity 的既有概念，保留 `race_source_value`、身份键、source SHA、Person/Visit 关联、Fingerprint、Writer Claim/Fencing 和原子 SQL。若需要在 Spark/Writer 边界增设前置检查，须复用同一允许集合、避免两套漂移的枚举，并在 COMMIT 以前给出可读的字段和值。
3. **有意义的长期测试**：添加 `native` 正例、全部已有合法 Race 正例、非法值负例、规范化/空值、确定性 Fingerprint 和批次行数检查，失败不落库。代码和测试采用组件能力命名，不新建 taskNNN/stepNNN 文件。
4. **验证与交接**：静态/Unit/Contract 先 PASS；再用失败历史 Parquet 做旧/新/修复后只读映射对照（64 Person/12,446 Visit）；修复源码/测试 PR 合并 Main 后，由 [原迁移 Task 4.11.5](../relocate-local-data-platform/tasks.md) 从准确 SHA 构建发布受影响镜像、检查实际 Pod Digest、新生成独立 Batch 真实 E2E、PG/S3 Readback、同 Batch SKIP/PG 零变化。
5. **回退与停机条件**：词表定义冲突则 HOLD；代码可按固定 Git SHA 回退，镜像按不可变 Digest 恢复；已发生的 PG/S3 写入不能依靠 Git Revert 自动恢复。不得为了验证清库或重复提交历史成功 Batch。

## Alternatives Considered

- 继续随机运行直至偶然 PASS：会掩盖未覆盖的合法数据。
- 对所有未知 Race 强制写入 `0`：掩盖有效语义。
- 清空 PG 回放上午成功 Batch：不必要且破坏既有 Ledger/幂等事实。

## Verification

本方案 PR 不执行任何共享资源操作。修复阶段须记录准确源码 SHA、单元测试/真实只读对照和后续新镜像 E2E Run 证据；仅映射 PASS 不代表 Atomic Writer COMMIT PASS。
