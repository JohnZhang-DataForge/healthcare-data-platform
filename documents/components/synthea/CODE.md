---
status: active
scope: synthea-apps-source-map
last_verified: 2026-10-16
source_sha: e26d8032deaab8ae4cfdbc1d446eceb5d9dc8ac9
---

# Synthea Producer — CODE / 源码导航

> 本页是该组件的**唯一源码地图**。基于上述 Git SHA 的源码和功能边界分类；不重复当前项目状态或运维 Runbook。组件概览见 [README.md](README.md)，运行安全门槛见 [Safe Operations](../../operations/SAFE-OPERATIONS.md)。

## 独立 NEW_ONLY Producer（正式入口）

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`entrypoint.py`](../../../apps/synthea/new_only/entrypoint.py) | 独立 NEW_ONLY 多阶段运行入口；显式 fail-closed |
| [`generate_new_only.py`](../../../apps/synthea/new_only/generate_new_only.py) | 固定请求与 Seed 的本地 CSV 生成器；不发布 READY |
| [`preflight.py`](../../../apps/synthea/new_only/preflight.py) | Producer 的 K8s / 存储只读预检 |
| [`prepublish_gate.py`](../../../apps/synthea/new_only/prepublish_gate.py) | 生成后、上传前的本地发布安全校验 |
| [`publish_v1_verified.py`](../../../apps/synthea/new_only/publish_v1_verified.py) | NEW_ONLY v1 S3 不可变发布 |
| [`publish_v2_verified.py`](../../../apps/synthea/new_only/publish_v2_verified.py) | NEW_ONLY v2 S3 不可变发布 |
| [`verify_v1_ready.py`](../../../apps/synthea/new_only/verify_v1_ready.py) | v1 READY 的全对象校验与只读读回 |
| [`verify_v2_ready.py`](../../../apps/synthea/new_only/verify_v2_ready.py) | v2 READY 的 18 CSV 和 Manifest 只读读回 |

## 历史 Producer / S3 发布兼容代码

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`validate_synthea_batch.py`](../../../apps/task001/validate_synthea_batch.py) | 历史 TASK001 18 CSV/Schema/SHA 验证 |
| [`publish_synthea_landing.py`](../../../apps/task004/publish_synthea_landing.py) | 历史 v1 发布模块，仍为部分 NEW_ONLY 路径复用 |
| [`validate_generated_synthea_batch.py`](../../../apps/task004/validate_generated_synthea_batch.py) | 历史 TASK004 生成数据本地校验与 Manifest 构造 |

## 关联入口

[独立镜像](../../../images/synthea-new-only/Dockerfile) · [K8s Job 模板](../../../kubernetes/manifests/synthea/new-only/) · [Synthea Contract](../../../contracts/synthea/producer-batch-identity-v1.json) · [Producer Tests](../../../tests/synthea_new_only/)

`publish_synthea_landing.py` 的旧版接口仍被新的 v1 路径复用，不能为了重排目录改变它。

## 源码维护约定

**新增、删除、重命名或移动本组件负责的 `apps/` 源文件时，必须在同一个 PR 更新此 CODE.md。** CODE.md 只做导航，不能当作重新执行历史脚本的授权。历史 `taskNNN` 程序仍可能被 Docker COPY、Import 或冻结 Contract 引用；先看 [Legacy 重构计划](../LEGACY-CODE-REFACTOR-PLAN.md)。

