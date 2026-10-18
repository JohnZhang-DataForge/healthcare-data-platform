---
status: active
scope: portal-spark-openlineage-source-map
last_verified: 2026-10-18
source_sha: ad39ed608c699ea3f30b74bd4bc331733d462e99
---

# Spark OpenLineage — CODE / 静态源码地图

> 本组件是**隔离 Spark/Marquez Smoke**，不负责已验收 Person/Visit Spark 业务 DAG/Writer。组件职责与失效门槛参见 [README](README.md)。

| 源码文件 | 用途 |
| --- | --- |
| [`input.csv`](../../../../platform-portal/openlineage/spark/input.csv) | 3 行人工 CSV 测试数据；非真实 Synthea/OMOP 数据 |
| [`probe.py`](../../../../platform-portal/openlineage/spark/probe.py) | Spark CSV 只读计算和验证，不执行业务 Writer/S3 提交 |
| [`sparkapplication.yaml.tpl`](../../../../platform-portal/openlineage/spark/sparkapplication.yaml.tpl) | 隔离 SparkApplication v1beta2 模板、资源限额、per-job Listener / Marquez HTTP Collector |
| [`render.py`](../../../../platform-portal/openlineage/spark/render.py) | **离线**渲染唯一名称 ConfigMap + SparkApplication YAML；自身不向集群 Apply |
| [`requirements-static.txt`](../../../../platform-portal/openlineage/spark/requirements-static.txt) | 静态验证环境依赖 |
| [`tests/test_static.py`](../../../../platform-portal/openlineage/spark/tests/test_static.py) | 离线 unit tests；未运行 Spark/K8s/API/数据库 |

**示例离线操作**（需在已审查的本地 Python 环境执行；最后仅写本地 YAML，不会 Apply）：

```bash
python -m pip install -r platform-portal/openlineage/spark/requirements-static.txt
python -m unittest discover -s platform-portal/openlineage/spark/tests -p 'test_*.py' -v
python platform-portal/openlineage/spark/render.py --run-token probe01 > /tmp/portal-a4-probe01.yaml
```

任何真实 SparkApplication 创建、Self-Runner Live Smoke、S3/Parquet 写入和清理工作均需要另行授权。**不存在由本组件 CODE 赋予的自动部署许可**。

[系统 CODE](../CODE.md) · [Marquez CODE](../marquez/CODE.md) · [Data Platform Spark CODE](../../data-platform/spark/CODE.md)。
