---
status: active
scope: portal-spark-openlineage-source-map
last_verified: 2026-10-24
source_sha: ad39ed608c699ea3f30b74bd4bc331733d462e99
---

# Spark OpenLineage — CODE / 静态源码地图

> 本组件是**隔离 Spark/Marquez Smoke**，不负责已验收 Person/Visit Spark 业务 DAG/Writer。组件职责与失效门槛参见 [README](README.md)。

| 源码文件 | 用途 |
| --- | --- |
| [`input.csv`](../../../../platform-portal/openlineage/spark/input.csv) | 3 行人工 CSV 测试数据；非真实 Synthea/OMOP 数据 |
| [`probe.py`](../../../../platform-portal/openlineage/spark/probe.py) | 3 行合成 CSV 读取/分组计算 → 唯一 Token 的 PVC Parquet 实际写入 → Spark 再读回并校验；不执行业务 Writer/S3 提交 |
| [`sparkapplication.yaml.tpl`](../../../../platform-portal/openlineage/spark/sparkapplication.yaml.tpl) | 隔离 SparkApplication v1beta2 模板、Driver/Executor 共享 PVC、per-job Listener、显式 Spark appName 及 Marquez HTTP Collector |
| [`render.py`](../../../../platform-portal/openlineage/spark/render.py) | **离线**渲染唯一名称 ConfigMap + 1Gi local-path PVC + SparkApplication YAML（三文档）；自身不向集群 Apply |
| [`requirements-static.txt`](../../../../platform-portal/openlineage/spark/requirements-static.txt) | 静态验证环境依赖 |
| [`tests/test_static.py`](../../../../platform-portal/openlineage/spark/tests/test_static.py) | 离线正向/非法 Token 与输出路径、PVC 读写挂载、安全合同测试；未运行 Spark/K8s/API/数据库 |

**示例离线操作**（需在已审查的本地 Python 环境执行；最后仅写本地 YAML，不会 Apply）：

```bash
python -m pip install -r platform-portal/openlineage/spark/requirements-static.txt
python -m unittest discover -s platform-portal/openlineage/spark/tests -p 'test_*.py' -v
python platform-portal/openlineage/spark/render.py --run-token probe01 > /tmp/portal-a4-probe01.yaml
```

任何真实 SparkApplication 创建、Self-Runner Live Smoke、S3/Parquet 写入和清理工作均需要另行授权。**不存在由本组件 CODE 赋予的自动部署许可**。

[系统 CODE](../CODE.md) · [Marquez CODE](../marquez/CODE.md) · [Data Platform Spark CODE](../../data-platform/spark/CODE.md)。

> **P3 变更边界**：此版本生成持久化 Parquet 的目标仅为测试 PVC，和业务 S3/PG 完全隔离；每次独立 token，使用 `errorifexists` 禁止无声覆盖。真实 Job/Run/Dataset 读回与 PVC 权限仍 PENDING，不能仅凭静态通过认定 `unknown` 已修复。旧 A4 未写输出的历史结论仍有效。

## P4 Airflow → Spark 真实父 Run 上下文（源码实施，尚待新镜像/实机）

- Airflow `new_only_omop_consumer.py` 的三个 KPO 使用 **OpenLineage Provider 的真实 Jinja 宏**生成 Namespace、Task Job Name 和 UUID，而不是按 Airflow DagRun 字符串猜测或伪造 Run。
- [Spark context injector](../../../../local-data-platform/spark/common/openlineage_parent_context.py) 按精确 `new_only_omop_consumer.spark_{patient,encounter,reconcile}` 任务、private namespace、合法 UUID 验证后，仅向真实 SparkApplication 的 `sparkConf` 注入官方 `parentJobNamespace`、`parentJobName`、`parentRunId`。若 NEW_ONLY 缺值，渲染前 Fail Closed；旧无 opt-in 保持 YAML 不变。
- 既有三个 `scripts/task004/05{d,e,f}-...` 控制脚本在 kubectl dry-run/apply **之前**运行注入器；只有子镜像 [Dockerfile](../../../../local-data-platform/images/landing-processing-runtime/Dockerfile) 覆盖三脚本/新 helper。Spark PySpark 算法、S3 来源、OMOP Writer/Claim/Fencing 均未改变。
- [离线负向/正向测试](../../../../local-data-platform/tests/spark/test_openlineage_parent_context.py) 和 P4 Existing Static Workflow 只验证源码逻辑。**下一次需要新 V2 镜像 Clean Build/Smoke/显式发布，再用全新 Batch 实机检查真正的 Airflow→Spark ParentRunFacet；不复写历史 #40125211881 的失败结论。**
- 该注入器不涉及 Spark 子 Run `RUNNING` 的终止事件修复。Listener 生命周期问题需要独立真实 Driver 日志/Marquez 读回证据。

## P4 NEW_ONLY 业务 Listener（2026-10-24）

隔离 `platform-portal/openlineage/spark/sparkapplication.yaml.tpl` 是已验证 P3 探针，**不作为业务 Pod 的执行模板**。本轮按最小修改接入真正的 `NEW_ONLY` 三个 SparkApplication：
- [Person 模板](../../../../local-data-platform/spark/manifests/task002/person-canonical-adapter.yaml.tpl)：合成患者 CSV/Manifest → 实际 S3A Processing Parquet，可验两侧 Dataset；
- [Visit 模板](../../../../local-data-platform/spark/manifests/task003/encounter-canonical-adapter.yaml.tpl)：合成 Encounter CSV → 实际 S3A Processing Parquet，可验两侧 Dataset；
- [Reconcile 模板](../../../../local-data-platform/spark/manifests/task004/person-visit-reconciliation.yaml.tpl)：只读两个 Processing Parquet，**没有输出写入**，只期待输入 Dataset。

镜像负责正确模板生效：[NEW_ONLY v2 child Dockerfile](../../../../local-data-platform/images/landing-processing-runtime/Dockerfile) 将这三个模板覆盖到父镜像原路径；基础父 `task004-runtime` 及三个 PySpark 业务算法不需要重建/修改。Airflow `latest` 不改；单独执行镜像 Clean Build、no-network Smoke、精确 Digest 晋级后，新增 Pod 才可拉取新版。配置复用 P3 成功的 OpenLineage Spark package `1.47.1` / Listener / Private Marquez API；Namespace 独立使用 `healthcare-platform-spark-business`，真实 Job appName 使用每个实际 SparkApplication `__APP_NAME__`，不伪造 parent facet 或 Writer COMMIT。

[离线 P4 Contract Tests](../../../../.github/quality/tests/test_portal_p4_spark_listener.py) 严格检查三组实际业务模板 Listener/Source/S3A/I/O/子镜像版本闭包。[P4 GitHub Hosted CI](../../../../.github/workflows/portal-p4-business-spark-static.yml) 首先运行离线 Listener/真实 Parent Source/GET-only 合同测试，再在 PR 上单独 **Clean Build 仅一张 V2 子镜像**：从现行 GHCR 拉取已有 TASK004 Parent 并解析为不可变 Digest，按 PR HEAD 构建、复用 allowlisted single-image smoke 在 `--network none`、drop caps 容器内检查真实脚本和注入器。该受控 CI 只具 GHCR `packages:read`，无 `docker push` 或 `latest` 修改，也不启动 K8s/Airflow/Spark；**Packaging PASS != 已发布镜像 Digest != 新批次 E2E**。`Writer` 和 PG 真实提交仍由 P5 控制及独立读回，不从 Spark COMPLETE 推断。
