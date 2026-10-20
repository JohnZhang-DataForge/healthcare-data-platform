# TASK003 STEP06C3 CDM Materialization Preflight 冻结生成器退役（2026-10-20）

> OpenSpec Change: `relocate-local-data-platform`, Task **4.9 PARTIAL**。仅删除一个历史源码**安装生成器**，保留已在 Git 中正式维护的业务前置验证源码及其测试；无数据库/S3/Kubernetes/镜像发布/历史批次变更。

## 1. 删除范围与不可变恢复地址

- Healthcare 起始 Main: `ac687129d41792b1ace54333c01a89b3544ca85b`; Self-Runner Main: `4561f666d99e4fe1b014acac65332d5215b0c0c8`。创建分支时无未合并的 Healthcare PR。
- 退役路径：`local-data-platform/scripts/task003/06c3-prepare-cdm-materialization-preflight.sh`
- 原 Git Blob SHA: `52ef3b8000f56f16cdcaf0d0313ead06e3030a71`，与历史 94/94 Task003 Shell 分类矩阵一致：[矩阵](LOCAL-DP-TASK003-SHELL-TRIAGE-20261019.md)。原源码 [immutable Main recovery link](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/ac687129d41792b1ace54333c01a89b3544ca85b/local-data-platform/scripts/task003/06c3-prepare-cdm-materialization-preflight.sh)。历史原 393/393 源备份核对在 [独立备份证据](LOCAL-DP-BACKUP-BLOB-READBACK-20261019.md)；这不是最新 K8s/数据库对象备份。
- 此旧 Shell 固定在 `/data/spark/healthcare-data-platform` 旧目录，写入一套固定历史 Batch 的 Source/Contract/Tests。原 `docs/task003/TASK003-STEP06C-CDM-Visit-Materialization-Preflight.md` 文稿未跟踪进入当前 Git Tree；历史生成文稿来源仍可通过不可变原脚本中的 heredoc 取回，不将其描述为已备份的独立 tracked Markdown。
- `06c4e-prepare-committed-cdm-visit-materialization.sh` **没有删除**：它虽有三个已比对源码产物 3/3 一致，仍含基于冻结输入参数动态生成的 JSON Contract，不将部分产物比对冒充完整闭包。

## 2. 已保留的正式 Git 文件（6/6 字节相同）

从旧生成器每个 `cat > "$STAGE/<relative path>" <<'<HEREDOC>'` 的单引号 heredoc 中精确提取内容，再独立从当前 Main Git Blob 读取全部内容逐字节比较，**6/6 MATCH**：

- `local-data-platform/apps/task003/candidate_to_cdm_preflight.py` — **MATCH；KEEP**
- `local-data-platform/scripts/task003/06c2-candidate-to-cdm-column-preflight.sh` — **MATCH；KEEP**
- `local-data-platform/spark/contracts/processed/visit-cdm-materialization-preflight-v1.json` — **MATCH；KEEP**
- `local-data-platform/apps/task003/verify_cdm_materialization_preflight.py` — **MATCH；KEEP**
- `local-data-platform/scripts/task003/06c3-verify-cdm-materialization-preflight.sh` — **MATCH；KEEP**
- `local-data-platform/tests/task003/test_cdm_materialization_preflight.py` — **MATCH；KEEP**

另外新旧运行时所需的 Python/SQL/Job 创建等其他模块不在本次文件删除范围，绝不能将正式运行脚本从旧 Shell 名称推断为冗余。

## 3. 消费者范围、完整性边界和当前回归

- 固定 Main 中 **66/66** Healthcare 高优先入口（Workflows / Airflow DAG / Dockerfiles / Task004 Shell / image Shell）、**86/86** Task003 Shell、Self-Runner **16/16** 相关 OMOP/Visit/Healthcare Workflow 均已逐文件读取；对退役生成器的**精确文件名**进行字面调用扫描：**168/168 无直接命中**。Source CODE Map、OpenSpec 历史冻结资料是预期文档引用，不是运行调用。此结果**不能排除**变量拼接、外部 Runner/旧镜像、剩余测试的动态消费者；不把本批说成整个 4.1 / 4.8 闭包。
- OMOP `documents/systems/data-platform/omop/CODE.md` 的 STEP06C3 安装生成器当前导航条目已退役，历史 Task003 入口数由 **27→26**；为原脚本提供 immutable Git 只读恢复链接，保留全部六个源码产物和测试。
- 完整新业务 NEW_ONLY 的真实运行证据已存在：[Synthea READY Run #39421910846](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39421910846)、[Airflow Helm GitSync Run #39422344924](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422344924)、[Spark/Writer/PG Readback/Skip Run #39422787433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422787433)。这只证明现行完整链路正常，不代表已重新执行旧 STEP06C3 生成器。
- 本次仅通过 GitHub API 更改源码/导航/OpenSpec。**没有执行旧脚本**、没有创建 Spark/Kubernetes Job、没有改 PostgreSQL、S3、Secrets、Helm 或业务 Batch。
- 合并前必须绑定 PR **最终 HEAD** 验证 GitHub CI：OpenSpec Change/Static、Component Code Naming、Relative Links、Local DP provenance、Airflow 3.2.2 DagBag/Source、Docker isolated build、Writer 与 CDM reader regressions。任何失败先诊断，不能绕过，不能在全部 CI 成功前合并。
- 4.9 Task 仍 **OPEN/PARTIAL**；4.1/4.8/4.10/5 未完成，后续按依赖和恢复证据继续清理。
