# Tasks — Platform Portal Real Business Lineage MVP

> **STATUS: ACTIVE / PLANNING & STATIC INVENTORY STARTED.** 本 Change 优先交付 Portal；`modernize-legacy-task-code` 命名及结构实施暂停，但原 Change 保留 Active，不伪称关闭。尚未批准任何共享 K8s/PG/S3 变更；勾选源代码静态工作不等于运行验收。

## 1. P0 — Scope and plan

- [x] 1.1 只读核对当前 Healthcare Main、Portal A3/A4 历史证据、真实 `new_only_omop_consumer`/控制容器和 Portal 组件边界；确认没有同主题开放 PR。
- [x] 1.2 建立本 Change 的 Proposal / Design / Delta Specs / Tasks，定义“现有 Task/Step 命名不动、先业务血缘”的交付范围、依赖、风险和可测试验收。
- [x] 1.3 规划 PR [#412](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/412) 最终 HEAD `b49f87f0f98738cab2ba112bd24184503ea9aa47` 的 OpenSpec Strict [#40090292733](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40090292733)、Trusted Change Gate [#40090292723](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40090292723)、Change Gate [#40090292728](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40090292728)、Docs Links [#40090292741](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40090292741) 均 SUCCESS，已 Squash Merge 到 Main `a407ccf8c7de60aa5a79617fd3df86dde2685dbf`；该 PR 仅 OpenSpec 文档，无 Runtime 修改。

## 2. P1 — Marquez / PG14 read-only live baseline

- [x] 2.1 静态盘点既有 Helm/PG14/Marquez、A3 Provider/A4 Spark Listener 源码，标注 `deploy.sh`/`recover-web.sh`/`configure-scheduler.sh` 会修改资源，不能当作只读诊断。
- [x] 2.2a 已编制仅执行固定 `kubectl get` 且要求精确 context 的 K8s 资源盘点脚本与纯离线测试；只检查 Namespaces、Deployments、Services、EndpointSlices、PG14 Pod/PVC，明确标记 HTTP / PG SQL / Job-Run-Dataset 未检查。尚未执行 Live 查询。
- [ ] 2.2 核对共享环境占用与操作许可，使用受控只读命令检查 `dw-marquez` API/Web、Service/Endpoint、`dw-postgre14` PG14/PVC、健康/Namespace 及历史事件；记录时间、执行环境、实际源码 SHA。
- [ ] 2.3 保存健康报告和异常矩阵；未证实则 `LIVE_STATUS=UNKNOWN`，不自行重启或重装。

## 3. P2 — Airflow real business opt-in

- [ ] 3.1 只读核对 A3 Provider/Transport/Selective 现行生效位置，设计业务 DAG 的最小 opt-in 改动和负向防扩散测试。
- [ ] 3.2 仅修改真实 `new_only_omop_consumer` 所需最小配置，保留 DAG ID/Task ID/XCom/Claim/Fencing/Writer 许可；更新 Airflow CODE/测试并通过 PR CI。
- [ ] 3.3 受控验证真实 Airflow Job/Run 读回及其他 DAG 默认行为；明确 Proven vs Not Proven。

## 4. P3 — Spark A4 real I/O and Job/Run fix

- [ ] 4.1 对现有 A4 `unknown`、Job latestRun 空、Dataset I/O 0 的事件/facets 做只读溯源，冻结根因证据；原 Workflow FAILURE 记录不覆写。
- [ ] 4.2 在独立隔离 fixture 中定义实际输入与持久化输出 Dataset，修复 per-job Listener/Job/Run（依赖和测试固定），代码静态、负向测试通过。
- [ ] 4.3 经授权进行隔离 SparkApplication Live Smoke，核对 Event job/run 名称和真实两个方向 Dataset API 图；保留失败 Run/资源归属。

## 5. P4 — Real Person / Visit / Reconcile integration

- [ ] 5.1 对照实际 SparkApplication Renderer/Control Runtime/Image，设计不触碰业务算法的最小 Listener 接入；定义可核验的 Batch/DagRun/Spark Run/Dataset 身份映射。
- [ ] 5.2 业务模板/包装层及受影响镜像精确改动，补全 CODE/单测/负向回归；只重建受影响的镜像和其必要父子依赖，避免无关 8 镜像重建。
- [ ] 5.3 对真实 Person、Visit、Reconcile 运行核对 Marquez events/edges；禁止人工伪造 parent/COMPLETED event 补洞。
- [ ] 5.4 Writer 业务提交的可信状态关联方案：复用现有真实执行结果和 PG17 readonly Ledger/Checkpoint/CDM readback，不改变事务/Fencing，不凭 Spark COMPLETED 认定 Writer COMMIT。

## 6. P5 — Fresh synthetic batch end-to-end acceptance

- [ ] 6.1 在运行窗口核对代码 SHA、Image digest、GitSync、活跃 Job/Session、权限与资源独占，获得具体 Live 运行授权；不对已提交 Batch 盲重放。
- [ ] 6.2 使用至少 1 个独立全新合成 Batch 完成 READY → Airflow → Spark → Writer 原子 COMMIT → PG17 独立读回；理想为 2 个不同新 Batch，记录明确覆盖范围。
- [ ] 6.3 对同 Batch 重跑应安全 SKIP 且 PG17 业务数据零变化；验证 Claim/Fencing/错误 Manifest/Listener 不可用等适用的非回归或失败边界。
- [ ] 6.4 以同一真实 batch_id/manifest_sha256 关联 Marquez Airflow/Spark/Dataset 和 Writer 读回；完成证据矩阵并明确仍然不能观测的环节。

## 7. P6 — Native Marquez showcase and closeout

- [ ] 7.1 完成内网 Marquez 官方 Web 的可复现演示和只读查询说明；不裸露 NodePort 30999 到公网，不开发自研 UI。
- [ ] 7.2 同步 `documents/systems/platform-portal/` README/CODE、项目状态及 OpenSpec：只有 Live 已验证的结果标记为完成。
- [ ] 7.3 全部相应真实验收、Merge/Main/Run 证据确认后才申请 Archive；独立 Dashboard/公网只读展示属于未来独立 Change。

**Next action after this planning PR:** 2.2 当前服务/历史事件的受控只读 Live Inventory，随后并行推进 3.1 / 4.1。未满足运行安全门槛时 HOLD Live，但可继续无副作用源码/静态测试。
