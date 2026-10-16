# Landing S3 Batch Discovery — READ-ONLY 真实验收（2026-10-13）

> **源码与真实 SeaweedFS 完成一轮闭环：PASS。** 注意：本阶段交付的是**独立 S3 探测核心程序**，**不是**已调度的 Airflow DAG，也没有领取批次、触发 Spark 或执行 PostgreSQL COMMIT。所有新增工程文件采用功能名而非 task 编号。

## 已实现

- 独立程序：`apps/landing_discovery/scan_ready_batches.py`；测试：`tests/landing_discovery/test_scan_ready_batches.py`。
- 使用 boto3 对 `health-landing` 的 `source=synthea/source_version=v3.3.0/` 前缀执行**分页只读 LIST**，仅检查完整 `/manifest.json`，因此只上传 CSV 的部分批次不会被消费。
- 使用原先经过真实验证的 `resolve_verified_landing_file.validate_manifest` 检查 status=`INTAKE_VERIFIED`、批次/路径 lineage、18 CSV 元数据与 checksum fingerprint、S3 publisher readback 标记，计算实际 Manifest SHA256，返回稳定的 `batch_id/manifest_uri/manifest_sha256`。
- 安全限制：Manifest 大小 <=1 MiB；最多检查 1000 个 Manifest（超出 fail-closed）；同一 Source/Batch ID 重复发布 fail-closed；S3 访问失败 fail-closed；**旧格式/格式不合法的 Manifest 单独隔离并报告，不会拖死所有新的 READY 批次**；未验证的不会被返回为 READY。此阶段只检查已有生产者声明的 readback 标志，并**未在扫描时重新下载 18 CSV 字节**；后续消费者真正领取前必须再次校验源。
- 扫描不会写 S3、PG，不调用 Generator，不依赖 Airflow 是否在线；单次运行只输出可处理候选的 read-only inventory，不能把它当作 batch claim/COMMIT 授权。

## GitHub Actions 与真实集群证据

| 轮次 | Run | 结果/教训 |
|---|---|---|
| 1 | [38459264996](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38459264996) | FAIL；Kubernetes ConfigMap 挂载包含符号链接，Python `Path.resolve()` 将寻找 sibling 源码的路径解析到 timestamp 子目录；改为 `Path.absolute()` 修复。 |
| 2 | [38459947574](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38459947574) | FAIL；S3 中发现真正的旧版 Synthea Manifest 缺 `payload_fingerprint`。修改为逐对象 quarantine，不降低 READY 验证合同。 |
| **3** | **[38460137577](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38460137577)** | **SUCCESS**：8 单元测试 PASS；worker02/dw-spark 临时只读 Pod 使用现有 digest-pinned runtime + S3 Secret，真实分页读取 SeaweedFS，`DISCOVERED_READY_BATCHES=6`、`QUARANTINED_LEGACY_MANIFESTS=1`、`LANDING_DISCOVERY_REAL_S3_READONLY=PASS`、`DAG_TRIGGER=NO`、`DATABASE_MUTATION=NO`；Job/ConfigMap cleanup。 |

最终测试精确 Healthcare feature HEAD **`ffb238f529de7df7c591e90c192436efaa7efe85`**（随后只增加文档 checkpoint；程序和单测源码未变）。对应 Self-Runner workflow HEAD **`445671bf3301e68445937baf691760690eb38fd3`**。新文档合并后必须按 Main 真实 SHA 记录，不能将上述 feature HEAD 当成 Main。

## 下一开发环：Airflow 定时真正发现 S3（尚未实施）

**建议功能名**：`landing_batch_discovery`（Airflow DAG），`landing-discovery-runtime`（独立只读 image），不要沿用编号命名；旧 `task004_processing_pipeline` 冻结保留、绝不修改或重新调用 Generator。

1. 用已验收 Scanner 构建独立 GHCR 镜像并固定 digest；确保程序入口与 S3 Secret 的最小权限配置，并测试容器内的真 S3 读取。
2. 创建有周期 schedule 的 **opt-in 初始暂停** DAG（如每 15 分钟）；用 KPO 运行只读 Scanner，真实 Airflow DagBag parse、gitSync、单次手动触发核查，不启动 Person/Visit/Synthea，不允许写库。**调度部署与是否解除暂停必须经过受控验证。**
3. 进一步开发**独立的原子 Batch Claim/Ledger**（不是本轮内容）：拿到 READY Manifest 以后先区分 COMPLETED/SKIP、PROCESSING/锁、FAILED/RETRY、冲突/BLOCK，再按批触发已有 Spark Person/Visit。
4. 随后才接动态 OMOP Writer 的真正 COMMIT、DB Reconciliation、Replay/Recovery。旧批次可用于只读/Processing 校验，但不能把已有重合 Source ID 的历史批次强制写库。

**当前真实状态：S3 Discovery CORE = REAL S3 READ-ONLY PASS；Airflow SCHEDULED DISCOVERY = NOT IMPLEMENTED；POSTGRES DYNAMIC COMMIT = NOT IMPLEMENTED；TASK004 IN PROGRESS；TASK005 ON HOLD。**
