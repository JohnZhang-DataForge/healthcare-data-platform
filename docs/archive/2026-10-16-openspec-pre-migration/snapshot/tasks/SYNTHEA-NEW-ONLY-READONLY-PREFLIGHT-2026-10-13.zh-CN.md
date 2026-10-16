# Synthea NEW_ONLY — worker01 只读环境与 Contract 预检（2026-10-13）

> **NEW-A READ-ONLY AUDIT = PASS（已发现阻塞，不等于部署就绪）**。Self-Runner [Run 38481854395](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38481854395) / Artifact `synthea-new-only-preflight-38481854395` ID `11857670935`。精确 Healthcare feature SHA `3ea626496b1e3c326828402f486ae903fbd48d03`；操作层 Self-Runner workflow SHA `e4037dd606ea935e320805ee0ca5bf5349159522`。此次无生成、无 S3 发布、无新 Pod/PVC、无 DB DML；仅 `kubectl get`/node stats 只读请求、源代码 Contract 审查、3 个离线测试。

## 真实 worker01 / Namespace / Storage 结果

| 检查 | 观测值与结论 |
|---|---|
| worker01 | Node Ready=true，未设置 unschedulable；报告的 ephemeral-storage capacity `306453440Ki` **是 capacity，绝非可用新专用盘容量** |
| dw-synthea | Namespace 存在；有 2 个旧历史 Synthea Pod，均 worker01 / Succeeded；**不代表新 Generator 已部署** |
| NEW_ONLY dedicated PVC | **0**；没有可直接复用的独立持久数据卷 |
| StorageClass `local-path` | provisioner `rancher.io/local-path` / WaitForFirstConsumer / **Delete**，不符合专用持久盘目标 `Retain` |
| `seaweed-local` / `postgres-local` | 两者都为 Retain，但用途独立；不得借用 SeaweedFS 或 PostgreSQL 的现有卷 |
| SeaweedFS PV | worker01 上已有 3 个 Retain/hostPath PV，路径位于 `/data/seaweedfs/...`；**绝不可重用** |
| LocalPath provisioner 配置 | 读回没有可确认的 worker01 特定路径；实际 host mount 设备、文件系统、剩余空间和独立目录均 **NOT VERIFIED** |
| S3 Secret | 测试固定猜测名 `dw-synthea-s3` 返回 **NOT_CONFIRMED**（可能不存在、另一个名字或权限限制）。不可据此断言系统没有 S3 Secret；下一轮必须只读列出该 Namespace 的 Secret **名称**，不打印值 |

**硬 Gate：** 在确认 worker01 主机实际设备/mount/可用空间、不会与 SeaweedFS 路径重叠后，建议规划独立 `Retain` 静态 Local PV + `RWO` PVC + `worker01` nodeAffinity，Pod 挂载 `/synthea-state`。未核实时禁止创建 PVC 或启动生成 Job；从 Kubernetes API 的节点容量不能推断“专用物理盘已经存在”。

## Synthea v3.3.0 与 18 CSV

- 既有 Dockerfile 固定 `v3.3.0` / `995cf2fd33e67918d4e33110d9f68ad248002221`。历史 `images/synthea/entrypoint.sh` 强限制 `POPULATION_SIZE=20/50`，故不能直接用于 NEW_ONLY 目标 1–100。
- 交叉检查 **对应版本标签** Synthea 官方源 `src/main/java/App.java`（`https://github.com/synthetichealth/synthea/blob/v3.3.0/src/main/java/App.java`）：`-s` Seed、`-cs` Clinician Seed、`-r` UTC Reference Date、`-e` End Date、`-p` Target Population、`-o` 布尔 overflow 参数都存在；`-o false` 静态解析确认。**本轮没有执行 v3.3.0 Java CLI，也没有实际生成 1 人/100 人，运行态语义仍待 NEW-B/C 测试。**
- `contracts/synthea/v3.3.0/csv-contract.json`: **18 个唯一 CSV 文件 / `contract_version=1.0` / `require_nonempty_data_rows=true`（所有表都必须非空）**。小人口下某些 CSV 可能没有行；不能偷偷放宽此既有合同。必须以真实小批样本制定显式 versioned NEW_ONLY Contract，至少保证 Patient/Encounter 与完整 18 文件/Header，另定零行表策略并和 Consumer 兼容。
- `-o false` 不是数据完整性证明：必须以实际 `patients.csv` 行数 `1<=rows<=100`、去重、所有文件校验和验证。
- Source ID: 随机 Seed 不等于无冲突；NEW_ONLY 发布前还要对权威历史 Person 源键映射 read-only 查重。绝不能关闭 Writer drift protection。

## Legacy Writer ID Contract 的真实兼容负例

- `airflow/dags/task004_cdm_materialization_plan.py` 的 `_BATCH` 只接受 `^task004-airflow-[A-Za-z0-9._-]+$`。
- NEW_ONLY 推荐 `synthea-new-only-<request-id>`。预检在 Python **实际调用**既有 `plan()`：旧 `task004-airflow-compat-probe` 接受，新 `synthea-new-only-probe` 按设计抛 `BLOCKED=batch_id`。
- 下一步需要 versioned materialization/manifest/ledger ID Contract 显式扩展，既兼容旧已入库 Batch，又接受独立生产者 Batch；不得通过给新 Batch 假装加上旧 Airflow 前缀绕过约束。现有 Existing Target Drift 条件保持原样。

## 验收边界 / Next

```text
REAL_CLUSTER_READONLY_AUDIT=PASS
WORKER01_READY=TRUE
DW_SYNTHEA_NAMESPACE=EXISTS
NEW_ONLY_PVCS=0
LOCALPATH_DEFAULT_RECLAIM=Delete
DEDICATED_DEVICE_AND_FREE_SPACE=NOT_VERIFIED
SYNTHEA_CLI_SOURCE_FLAGS=VERIFIED_STATIC
SYNTHEA_CLI_RUNTIME_AND_SMALL_POPULATION=NOT_RUN
CSV_18_FILE_V1_AND_NONEMPTY=CONFIRMED
NEW_ONLY_WRITER_BATCH_ID_LEGACY=BLOCKED
GENERATOR_DEPLOYMENT=NO
S3_PUBLICATION=NO
POSTGRESQL_COMMIT=NO
TASK004=IN_PROGRESS
TASK005=ON_HOLD
```

**NEXT**：先补足 worker01 host mount/空间与 S3 Secret 名称的只读证明，定稿专用 `Retain` PV/PVC 方案；进入单独 NEW-B（NEW_ONLY 请求参数冻结、并发/重放、Synthea CLI/CSV 合同、Source ID Registry Check、Manifest 后发布代码/测试），真实部署和 S3 产出属后续独立 NEW-C，不自动授权。
