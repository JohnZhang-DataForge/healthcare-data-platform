# Local DP 迁移：第三轮全量静态清点与恢复门槛

> **2026-10-19 — 部分完成 / STATIC ONLY**。Healthcare `ea2d2e5ffd98c529c79626c7c926828a32fb7a7b`；Self-Runner `ffd0eccecbf0148183b956e6e4416d4b8d99002b`；备份 Healthcare-Specs `6089a2fcf934a26ea0c3fbb8dbdd11bc6f0a42a5`。本轮只通过 GitHub 读取固定提交的 Git Tree 和源码，**没有删除、回滚、Docker Build、CI 业务测试、Self-Runner Dispatch、Helm/K8s/PG/S3/Airflow/Spark Runtime 操作**。OpenSpec 4.1 与 4.8 仍然 **OPEN**。

## 已完成的覆盖度（文件级源文本清点）

| 范围 | 本轮覆盖 | 可追溯报告 |
| --- | ---: | --- |
| `scripts/task003/` | **94/94** Shell；每行 Git Blob、根路径类别、可能的资源操作、历史生成器线索及内部引用 | [Task003 全量文件审计](LOCAL-DP-TASK003-SHELL-TRIAGE-20261019.md) |
| `tests/` | **105/105** Test；每行 Git Blob、根路径使用、安全/Contract 关键词和文件引用样例 | [105 项 Test 审计](LOCAL-DP-TEST-TRIAGE-20261019.md) |
| Self-Runner `.github/workflows/` | **123/123** YAML；每行固定/动态 Checkout ref、旧/新路径出现次数、静态资源副作用线索 | [Self-Runner 全量 Workflow 审计](LOCAL-DP-SELF-RUNNER-WORKFLOWS-20261019.md) |
| Self-Runner `scripts/ci/` | **32/32** tracked CI 文件（含模板/演示项）；每行 Blob、旧路径正则和风险标记 | [Self-Runner CI 脚本审计](SELF-RUNNER-CI-SCRIPTS-20261019.md) |
| Backup 当前 Git Blob 对照 | **393/393 完全一致**；两仓完整 Git Tree、无遗漏、无内容差异 | [备份独立读回](LOCAL-DP-BACKUP-BLOB-READBACK-20261019.md) |
| Healthcare Core Workflows / `scripts/task004` | **21/21** Workflow 与 **14/14** Task004 Shell 已于前轮审阅 | [第二轮入口审计](LOCAL-DP-CROSS-REPO-CONSUMER-AUDIT-20261019.md) |

所有矩阵每项均标记 **HOLD**；这不是“要永远保留”，而是“没有完成删除安全证据”。文件级全覆盖不等于代码调用图全覆盖，更不等于实时部署已验证。

## 核实的重要结果

1. **TASK003 的历史生成过程相当重**：94 个 Shell 中，**73** 个源码含 `cat >` / `write_text` / `tee` 等文本生成线索；**51** 个因其文件名与生成线索被放到“Generator/History Candidate（待核查）”队列。这些数字**不是**可删除数量。**31** 个含明显旧宿主 Root 字面量。**61** 个含 `kubectl`、**30** 个含直接 `psql/psycopg/PGPASSWORD` 线索、**47** 个含删除命令类字面标记；部分可能仅在生成的 Shell 中出现。审查/移除须考虑间接调用、生成文件回写和失败恢复。
2. **测试价值需要保护**：105 个测试中，**91** 个含安全/Contract/Manifest/幂等/回滚等文本标记；只是关键词匹配，不等于 91 个都必须永久保留。但不能把 `tests/task003`、`tests/task004` 当垃圾批量删除。明确的优先问题仍是两份 Test 错将仓库级 `.github/workflows` 放在 Platform Root：
   - `tests/task004/test_synthea_ghcr_workflow.py`
   - `tests/task004/test_unified_runtime_image_source.py`
   这属于需要**修正并保留有效断言**的测试。
3. **Self-Runner 旧路径不能按关键字机械替换**：123 个 Workflow 中，**71** 个包含固定 40 位 SHA 的 Healthcare Checkout，**26** 个含动态/非固定 Checkout 表达式，**26** 个没有显式的 Healthcare `repository:` Checkout。**65** 个出现 `healthcare/apps/` 等历史源码路径文本，明确 `healthcare/local-data-platform/` 字面路径的条目为 **0**。但很多旧路径正好服务于固定历史 SHA：正确性取决于该运行的 Healthcare Checkout/Workspace 布局与当时的调用，**不能仅凭 65 个出现次数就认定迁移有 65 个 Bug**。32 个 CI 脚本未匹配本轮有限的字面模式，也**不证明没有动态路径间接依赖**。
4. **备份达到重要里程碑**：经两仓固定 Git Tree 逐路径/Blob SHA 双向比对，当前 393 个 Local DP 文件与私有 Healthcare-Specs 备份 **393/393 完全一致**，缺失 0、内容不一致 0、备份额外业务文件 0。迁移以来的 Local DP 文件仍未有源码增量，故**这些固定提交之间**不需补增量 Git 源码备份；将来一旦有修改必须重算。备份不包含数据库、K8s 持久卷、S3 对象和镜像恢复证明。
5. **目前能明确保护的代码**：`images/task004-runtime/Dockerfile` / Entrypoint 引用的五个历史 Shell、正式 DAG、Writer/Fencing/Claim 关键模块和具有独有防错价值的 Test。它们属于先保留后兼容修复/独立重构，不能为追求清理率直接删除。

## 需要继续完成的 4.1 / 4.8 安全证明

**本次新读过的 94+105+123+32 文件均为源码文本级分类，并未完成以下验证：**

- 内部 `Shell → Shell`、生成器 `Shell → Python/YAML/Workflow` 的全量调用/覆盖**图闭包**与每个候选 C/D 是否被当前维护入口可达；动态拼接路径、导入、Self-Runner scripts/ci 间接调用不能只靠 grep。
- 全部 105 Tests 的**实际**固定 SHA 可复跑性、失败原因、唯一断言覆盖、改名/迁移后的等价 Regression；测试关键词并不能替代测试执行。
- Airflow 当前 Helm GitSync 的 Repo/SubPath/DAG Sync 实际配置、DAG Parse/单一来源证明、SparkApplication 当前镜像/ConfigMap/JAR/PYTHONPATH 来源；这需要后续源码和按需**单独授权**的运行检查。
- 镜像 Clean Build 和 module `__file__` / Base Image 实际溯源、当前 GitHub Build Context 修复：仍在 Task 4.2–4.4 待实施，现阶段无 Build PASS。
- 每个待删除文件的消费者为零、存在合规替代、保留真正安全回归以及对应文件恢复 SHA；不允许由目录名或一次旧备份直接跳过这些 Gate。

## 下一小步建议

完成上述来源和调用闭包的**受控静态核查**后，先将 4.8 的恢复/依赖矩阵拆出首批**无动态消费者**、不承载独有断言的 C/D 小清理候选；暂不实际删文件。之后按已批准 OpenSpec 顺序：4.2–4.4 修正式编译/Workflow/Build/DAG 路径，才进入 4.9–4.10 分批删除和验证，最终经单独授权进行 4.5–4.7 的运行/E2E 验收。发生同一问题最多尝试三轮，无法证实即 HOLD，保存 Branch/SHA/Run 原因。

**结论：文件级审计和独立 Git 备份读回已经完成相当大的可重复核对工作；但 Task 4.1、4.8 均不得打勾，删除获准文件数目前是 0。**
