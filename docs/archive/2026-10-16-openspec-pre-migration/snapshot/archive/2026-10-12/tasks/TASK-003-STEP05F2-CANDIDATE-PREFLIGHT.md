# TASK-003 STEP05F1–F2C — Visit Candidate Preflight

验收日期：2026-10-09。

## 验收结论

STEP05F1–F2C 真实 Spark 内存映射验证通过。

- SparkApplication: `visit-cand-check-20261009t192437z-2081886`
- Spark 状态：COMPLETED
- APPROVED Raw Encounter：5799
- Visit Candidate：5799
- 唯一 Encounter key：5799
- 关联 Person：113
- Encounter Class：10 种，全部正确映射
- Candidate Schema、Person JOIN、Visit Concept、日期、必填字段与延后映射字段：PASS
- Visit ID 分配：0
- PostgreSQL 写入：NO
- S3 写入：NO
- Candidate 发布：NO

## 正式源码及重建入口

STEP05F1：

- `scripts/task003/05f-prepare-visit-candidate-mapping.sh`
- `apps/task003/visit_candidate_rules.py`
- `spark/apps/visit/map_encounter_to_visit_candidate.py`
- `spark/contracts/omop/visit-candidate-v1.json`
- `tests/task003/test_visit_candidate_rules.py`

STEP05F2A：

- `scripts/task003/05f2a-prepare-visit-candidate-driver.sh`
- `spark/apps/visit/validate_visit_candidate_preflight.py`
- `tests/task003/test_visit_candidate_preflight_static.py`

STEP05F2B / F2C：

- `scripts/task003/05f2b-prepare-visit-candidate-runtime.sh`
- `spark/manifests/task003/visit-candidate-preflight.yaml.tpl`
- `scripts/task003/05f2c-validate-visit-candidate.sh`

从新环境重建时，应先完成平台及 STEP05A–E 的上游依赖，再按照正式 prepare Shell 顺序生成源码，并使用 STEP05E 的已批准证据执行 F2C。

## 本次本地验收证据

`runtime/reports/task003/step05/candidate-preflight.AtnqkQJz/`

包括：

- `run-state.json`
- `driver.log`
- `candidate-preflight-input.json`
- `mount-sha256.json`
- `configmap-files/`
- `sparkapplication.yaml`

runtime 证据不提交 Git；仅 clone Git 不能恢复已发布数据或运行历史。

## 验收边界

STEP05F1–F2C 仅证明未发布的 Visit Candidate 内存映射正确。

未完成：

- Processed Candidate 持久化
- Processed DQ 与 APPROVED Manifest
- 数据库 Stage
- Visit 稳定 ID 分配
- OMOP `cdm.visit_occurrence` UPSERT
- CDM 对账及重复执行验收

后续继续遵循先数据质量验证、再发布、最后进入事务加载的规则。

完整干净环境端到端重建尚未验收。
