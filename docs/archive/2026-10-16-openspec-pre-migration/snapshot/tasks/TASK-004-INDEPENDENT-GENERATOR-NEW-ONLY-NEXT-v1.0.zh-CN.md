# TASK004 NEXT — 独立 Synthea NEW_ONLY Generator 开发与验收（2026-10-13）

> **仅 NEW_ONLY；设计已批准，代码/部署尚未开始。** 唯一目标：脱离 Airflow 独立运行 Synthea Job，随机合法州 / 人数（目标 1～100，实际 <=100）/ Seed / 当前创建日期，经 worker01 独立 LocalPath 持久化恢复，最后向 SeaweedFS 发布不可变 18-CSV Batch+verified Manifest。**不是**开发 EXISTING_ONLY / MIXED / 新 Airflow 消费 DAG / PostgreSQL COMMIT。
>
> **先读完整主架构**：[`TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md`](../architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md)。该文档覆盖历史“Airflow 发参数和执行 generate_publish”设计。

## 0. 冻结/约束

- 当前 `images/synthea/` / `images/task004-runtime/` / `scripts/task004/` / `airflow/dags/task004_processing_pipeline.py` 是历史已验证版本，**不要直接改到旧入口、不要删除**；NEW_ONLY 写在专用目录/镜像/Job 里。
- Producer 可以独立 CronJob、受控 Self-Runner Action、人工独立 Job 触发；**不经 Airflow**，无 Airflow XCom 或 Seed/State 入参。参数由 NEW_ONLY 程序自身创建并固定在 LocalPath。
- S3 verified Manifest 是消费者唯一 READY/接口；不要用“Job succeeded”代替 Manifest 完整 readback。
- `dw-synthea` 已被指定为 namespace，worker01 为节点；是否实际存在 PVC/挂载/权限需要只读核查，不得推测。
- 共享的 SeaweedFS、PostgreSQL 及旧生成批次不得擦除、overwrite 或重新随机生成；绝不改动 OMOP 漂移保护。TASK005 ON HOLD。

## 1. STEP NEW-A：持久化空间 + 现有合同比对（先只读）

**检查**：
1. 查询 worker01 已有 block filesystem mount、剩余空间、目标独立目录/设备；`local-path` StorageClass 与 provisioner 配置、PV/PVC reclaim policy；不能直接宣称 `local-path` 为独立硬盘。确认是否需新建静态 local PV / 新 StorageClass 与单节点亲和性。
2. 检查 `dw-synthea`、现有 namespace Secret/S3 访问边界与旧 Job 模板；计划新 PVC 在 `dw-synthea` 的 Pod 挂载 `/synthea-state`，`Retain` 并确保 pod 只放 worker01。不复用 SeaweedFS 的现有卷。
3. 读取 `contracts/synthea/v3.3.0/csv-contract.json`、`apps/task004/validate_generated_synthea_batch.py`、`images/synthea/entrypoint.sh`：当前旧入口只支持 `20/50`，18 CSV 有非空约束，现有 `-p 20` 生成过 23 人；新增入口需独立处理 `1..100` 与 `-o false`，拒绝实际输出超过 100。
4. 预审随机州合法名、Synthea v3.3.0 官方 `-s/-cs/-r/-e/-p/-o` 参数，不依赖当前 UTC 与 Node 本地时间混用。

**交付**：一个可核实的 read-only preflight checkpoint，列出实际 PVC/设备/路径和失败风险；**不写磁盘、不生成数据**。

## 2. STEP NEW-B：独立代码+受控单元测试

建议新增但尚未存在：

```text
apps/synthea/new_only/
  generate_new_only.py       # 独立业务入口：随机数/州/Seed/冻结/状态机
  persistence.py             # localpath 请求状态，atomic 写入/并发锁
  manifest_publisher.py      # S3 发布/GET checksum/readback，不允许覆盖
images/synthea-new-only/
  Dockerfile
  entrypoint.sh
kubernetes/manifests/synthea/new-only/
  job.yaml.tpl               # 受控短生命周期 Job；后续 CronJob 可选
tests/task004/
  test_new_only_*.py
```

- 业务入口只属于 **NEW_ONLY**；不在其代码里设计 `EXISTING_ONLY` / `MIXED` 运行分支。
- 生成请求 id 独立于 Airflow。新请求随机选择 State、target population 1～100、Seed、Clinician Seed、日期；在 LocalPath 以不可覆盖原子写/锁先冻结 `params.json`，并记录生成器版本、Job/request 身份、S3 批次前缀。相同 request 的恢复绝不重新随机化。
- Synthea 使用独立构建的固定 tag/digest，版本锁定；增量兼容现有 18 CSV 校验与 Manifest Contract。若小人口产生空表，必须通过真实测试决定 v2 契约处理办法，不可修改历史 v3.3.0 既有 CSV contract 让旧任务失效。
- Generator **完全不处理 OMOP 写库**；在发布前校验期望的新 Person ID 不重复、实际输出数量 <=100；对历史 source key collision 执行安全检查。碰撞校验需要具备权威来源，不能仅“换一个 Seed 就默认没冲突”。
- 可靠性测试：创建失败恢复、相同 request 参数固定、不同 request 参数不同（不可将随机不同视为绝对保证）、同 batch SHA 冲突 fail-closed、最后发布 Manifest、未完成批次不 READY、幂等重放、节点锁竞争。

**交付**：Healthcare feature PR + exact SHA、源码/测试/镜像构建入口；静态或容器测试证据。不得仅提交设想就写 PASS。

## 3. STEP NEW-C：部署与真实 S3 端到端验证（另一个有界循环）

**经明确授权后**：使用 Self-Runner/ARC 以固定 Healthcare SHA 创建/确认 dedicated PV/PVC（Retain，worker01）、在 `dw-synthea` 启动一次 NEW_ONLY Kubernetes Job。采集：

- K8s Pod 真正运行于 worker01；PVC Bound + 独立磁盘路径正确；Job 退出 0；参数文件留在 LocalPath 并可只读 readback。
- 真实随机人数 (1..100) 及州名合法，Reference Date 是请求创建时日期，真实 patients.csv 人数 `1..100`（不等于必然等于目标）。
- 在 S3 使用全新的 batch ID、校验 18 CSV、文件 SHA、Manifest 最后发布、`INTAKE_VERIFIED`、S3 readback=PASS，数据库在本 STEP 无变更。
- 重用**同一个 generation_request_id** 后不能产生不同参数或第二份 Manifest；重复执行不能覆盖原先 Batch。
- 自主生产验证时 Airflow 没有任何生成调用，未运行 PostgreSQL Writer。实测失败最多 3 次，停下做 checkpoint 而不是无界试错。

**真正成功才标注** `NEW_ONLY GENERATOR=PASS`，不是把已完成的历史 Airflow `generate_publish` 冒充新设计验收。

## 4. 后续单独 STEP：Airflow 消费端（本轮不开始）

等 NEW_ONLY 独立发布验证通过，再新建 S3 发现/领取 Batch 的 opt-in DAG；先读、再锁定 Manifest SHA/租约、只处理已存在 CSV，独立跑 Person/Visit、Writer、DB Reconciliation、Replay。在真实 COMMIT 充分授权前不能标成完整 TASK004 PASS。

## 5. 实施规则

一次开发 STEP 至少达到“源码/部署 + 相应验证 + 真实回读证据”的闭环；避免一次开发三种模式。所有变更走 Healthcare feature branch/PR + Self-Runner exact-SHA 证据 + merge 与 checkpoint；失败 >3 次停。**后两种模式始终 ON HOLD，直到 NEW_ONLY 验收 PASS 后由用户决定解锁。**

**当下 NEXT = NEW-A（只读持久化/合约 preflight） → NEW-B（NEW_ONLY 独立源码） → NEW-C（真实生成与 S3 readback）。** 此文档合并并不等于以上工作已经执行。
