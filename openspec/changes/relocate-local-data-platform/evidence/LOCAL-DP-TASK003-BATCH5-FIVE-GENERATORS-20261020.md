# Local DP Task003 第五批历史安装生成器退役证据（2026-10-20）

> OpenSpec Change `relocate-local-data-platform` / Task 4.9 **PARTIAL**。此批删除 5 个只承担旧代码物化/安装的一次性 Shell，绝不删除或重建它们已经纳入 Git 的正式源文件、验证和测试；不操作任何持久业务系统。

## 1. SHA、冻结历史来源与恢复

Healthcare 起始 Main：`0177ee3b466215492254803d28dfa4de06eff244`；Self-Runner Main：`4561f666d99e4fe1b014acac65332d5215b0c0c8`。开分支时 Healthcare 无待合并 PR。下列当前源码 Blob SHA 均与过去 [94/94 Task003 Shell 分类记录](LOCAL-DP-TASK003-SHELL-TRIAGE-20261019.md) 的历史 Blob 一致，处于之前核验的 Healthcare-Specs 独立源备份集合，可通过固定 Git 历史精确恢复：

| 删除的源码安装生成器（`local-data-platform/scripts/task003/`） | Frozen blob | 不可变历史来源 | 保留正式产物 |
| --- | --- | --- | ---: |
| `05g1-prepare-visit-processed-plan-validation.sh` | `c3663ddcfd75352c74b65ee3eb635353859b85cf` | [Git history](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/0177ee3b466215492254803d28dfa4de06eff244/local-data-platform/scripts/task003/05g1-prepare-visit-processed-plan-validation.sh) | 3/3 |
| `05g2c2c2b1-prepare-bundle-inventory-source.sh` | `0c9d28f5021f4a1f705af659638a8510c83995ec` | [Git history](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/0177ee3b466215492254803d28dfa4de06eff244/local-data-platform/scripts/task003/05g2c2c2b1-prepare-bundle-inventory-source.sh) | 3/3 |
| `05g2c2c3d1-prepare-writer-observer.sh` | `ba368da5ca2db028caa4f10ae71be64aced3dc2e` | [Git history](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/0177ee3b466215492254803d28dfa4de06eff244/local-data-platform/scripts/task003/05g2c2c3d1-prepare-writer-observer.sh) | 1/1 |
| `05g3a-prepare-processed-dq-builder.sh` | `e2e62307871f48e9c48f3ca3b1bbcd5c0f373d73` | [Git history](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/0177ee3b466215492254803d28dfa4de06eff244/local-data-platform/scripts/task003/05g3a-prepare-processed-dq-builder.sh) | 3/3 |
| `05g4a-prepare-processed-manifest-builder.sh` | `88eb57fa3fa5f413f54a7e5d0883b08c8ac16e11` | [Git history](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/0177ee3b466215492254803d28dfa4de06eff244/local-data-platform/scripts/task003/05g4a-prepare-processed-manifest-builder.sh) | 3/3 |

## 2. 精确产物检查（13/13 MATCH）

从 **5 个当前 Git Bash 源文件**解析每个 `cat > "$STAGE/<relative>" <<'<TAG>'` 的字面 heredoc，逐一提取生成的完整 UTF-8 内容，独立 Fetch 当前 Healthcare Main 相同目标路径的 Git 文件，比较完整内容（不是只检查路径存在或关键词）：**13/13 一致**。以下所有正式源文件继续保留：

**`05g1-prepare-visit-processed-plan-validation.sh`（3/3）**
- `local-data-platform/apps/task003/verify_visit_processed_plan.py` — EXACT MATCH / KEEP
- `local-data-platform/tests/task003/test_visit_processed_plan_validation.py` — EXACT MATCH / KEEP
- `local-data-platform/scripts/task003/05g1-verify-visit-processed-plan.sh` — EXACT MATCH / KEEP

**`05g2c2c2b1-prepare-bundle-inventory-source.sh`（3/3）**
- `local-data-platform/apps/task003/prepare_visit_writer_bundle_inventory.py` — EXACT MATCH / KEEP
- `local-data-platform/tests/task003/test_visit_writer_bundle_inventory.py` — EXACT MATCH / KEEP
- `local-data-platform/scripts/task003/05g2c2c2b1-prepare-bundle-inventory.sh` — EXACT MATCH / KEEP

**`05g2c2c3d1-prepare-writer-observer.sh`（1/1）**
- `local-data-platform/scripts/task003/05g2c2c3d1-observe-visit-processed-writer.sh` — EXACT MATCH / KEEP

**`05g3a-prepare-processed-dq-builder.sh`（3/3）**
- `local-data-platform/apps/task003/build_visit_processed_dq.py` — EXACT MATCH / KEEP
- `local-data-platform/tests/task003/test_visit_processed_dq_builder.py` — EXACT MATCH / KEEP
- `local-data-platform/scripts/task003/05g3a-build-processed-dq.sh` — EXACT MATCH / KEEP

**`05g4a-prepare-processed-manifest-builder.sh`（3/3）**
- `local-data-platform/apps/task003/build_visit_processed_manifest.py` — EXACT MATCH / KEEP
- `local-data-platform/tests/task003/test_visit_processed_manifest_builder.py` — EXACT MATCH / KEEP
- `local-data-platform/scripts/task003/05g4a-build-processed-manifest.sh` — EXACT MATCH / KEEP

这些 Shell 曾将生成的源码、验证命令和测试安装到旧固定 Context；部分同时 `install` 自己、`cp` 已存在的源文件，或在生成的 Runner 内容中包含可写 S3/PG/K8s 命令。**本次仅删除安装器自身**，没有执行它们或任何它们产出的运行命令；现有 DQ/Manifest 业务发布构建脚本、Writer 观察器、Bundle Inventory、Plan Validation 以及所有 13 份正式源码/测试原样保留。

## 3. 消费者范围和未覆盖边界

- 在完整、非截断的 Healthcare Main Git Tree 下实际读取高优先 CI/Workflow、Airflow、Docker、Image、Task004 Shell **66/66**；当前 Task003 Shell **85/85**；Self-Runner 同 SHA 下与 Healthcare/OMOP/Visit/CDM 相关 Workflow **16/16**。对 5 个待退役文件名进行逐文件精确字符串扫描，**167/167 均未发现从其他已扫描文件调用它们**，仅 5 个生成器自身源码出现自身名称；Owner CODE Map、OpenSpec 冻结证据的文本引用不等于有效运行调用。不能由此宣称变量拼接路径、外部 Runner 或所有历史 Test 都已证明无动态调用。
- 更新 `documents/systems/data-platform/landing/CODE.md`，本组件历史 Task003 活动入口数 **47→42**，移除 5 个已删除路径的活动引用，追加固定 `0177ee3b466215492254803d28dfa4de06eff244` Git 恢复链接。
- 之前新目录 NEW_ONLY 路线已在 [Synthea #39421910846](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39421910846)、[Helm/Airflow GitSync #39422344924](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422344924)、[Spark/Atomic Writer/PG Readback/Idempotent SKIP #39422787433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422787433) 实际运行通过；它们没有执行上述旧安装器，不能作为历史所有行为已重跑的证据。
- 本 PR Git 操作不执行 Kubernetes/S3/PG、Secret、Helm 或镜像发布，不重放以前 5799 条 Visit 的冻结 Batch。保持完整正式业务链路、回滚、Recovery、测试和当前维护源码。不能为提高删除数量批量删除未知 `tests/taskNNN` 或隐含 Writer Fencing 的 Shell。
- **合并门**：按 PR 最终 Head 的 GitHub Actions 运行 OpenSpec Change/Static、CODE Naming、Docs Links、Local DP Provenance/Source、Airflow 3.2.2 DagBag、isolated Docker images、NEW_ONLY Writer/CDM Reader 回归，全部 PASS 才允许 Merge；失败时保持 PR 开放、诊断、修复或回滚。
- 本批次只推进 Task 4.9，**4.1/4.8/4.9/4.10 和 5 继续 OPEN**；不以 13/13 静态比对冒充 K8s/PG/S3 全功能回归。

