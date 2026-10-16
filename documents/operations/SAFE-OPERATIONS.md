---
status: active
scope: safe-runtime-operations
last_verified: 2026-10-16
source_sha: d1962f79e1c7337c372de1aebfaaec87dfc7d1c8
---

# Safe Operations — 运行前检查与恢复边界

> **稳定操作原则，不是可直接执行的脚本。** 源自 [开发工作流](../development/DEVELOPMENT-WORKFLOW.md)、[历史经验](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/runbooks/development-lessons-cn.md)、[Portal](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/operations.md)、[Azure IaC](../../azure/infra-terraform/README.md)。本次文档迁移没有实测当前集群或 Azure 状态。

## 每次运行前五项 Gate

1. **许可范围**：明确本次是 Docs / Static / Unit / 只读查询 / 有副作用 K8s-Spark-Airflow / PG 或 S3 写入 / Terraform Plan 或 Apply；工具可执行不代表已获用户批准。
2. **资源占用**：检查 [Session Coordination](../development/SESSION-COORDINATION.md)、未合并 PR、Workflow Active Run、当前 DagRun/Task、SparkApplication/Pod 和共享资源；未知或发生冲突时 **HOLD**。
3. **版本/身份**：绑定 Healthcare SHA、Workflow 版本/Run、Namespace/环境、镜像 Digest、业务 Batch ID + Manifest URI/SHA；不要把历史 Run 判为新 SHA 的验收。
4. **副作用/回退**：确定是否修改共享 Scheduler/Operator、StorageClass/PVC、PG、S3、Secret 或 Azure State；失败后能否安全审计。名为 readonly 的 Workflow 也可能创建临时 Job/ConfigMap。
5. **独立读回**：真正成功按范围判定：静态检查、实际执行、持久写入、独立对账及安全清理不相互替代。保留失败原始结论。

## 组件保护

| 目标 | 允许先只读检查什么 | 没有单独批准不得做什么 |
| --- | --- | --- |
| K8s / Local Storage / S3 | Node/Provisioner/SC/PV/PVC/Pod/后端目录/S3 Manifest SHA | 删除/重建持久卷，修改路径/NodeAffinity，覆盖完成 Batch |
| Airflow / Spark | GitSync SHA、DAG Import、DagRun/TaskInstance、SparkApplication/Driver/Executor、镜像 | 随意 Unpause/Trigger、重启共享 Controller、重复运行已完成 Writer |
| PostgreSQL17 OMOP | Claim、Ledger、Stage、Checkpoint、ID Map、CDM 表/FK、角色 | 未知 Commit 后盲目重试；跳过 Fencing/Secret；改名 `etl.task004_*` |
| Marquez / PostgreSQL14 | API/Web、PG14 元数据、Service/Endpoint、访问面 | 将 NodePort 30999 当公网匿名只读服务，或误删 PG14 Retain PVC |
| Azure/Fabric | Existing Blob/Workspace、IAM、Remote State、Terraform Validate/Plan | 未批准 `apply/destroy`、重复建 Workspace、绕过 Notebook/Pipeline fail-closed |

**Terraform Plan 并非无外部副作用的纯本地操作**：会读取 Azure、连接/锁定远程 State，必须核对本轮操作范围。Fabric 三个 Item 仍为 Plan-only；没有真实业务 ETL。

## 失败和接力

- **失败、超时或结果未知不等于事务没有完成**。先保存环境与日志，读取实际状态、独立 PG Readback，再决定重试/恢复；冻结 Batch 禁止随意 Replay。
- **Retain != Backup**：SeaweedFS/PG14/PG17 持久卷、Terraform Remote State 的存在不能证明备份与恢复已演练。
- **Session 消失 != 资源已释放**：新 Agent 不得凭上一个 Session 的「Done」或过期时间推断 Pod/Job/PG 事务已经结束。
- **只读也有资源风险**：大查询、S3 全量扫描、某些 readonly 工作流可能消耗资源或启动 Job；按真实脚本判断。
- 验收记录必须包含实际 PR/Main SHA、Run ID、被测数据/环境、原始 PASS/FAIL、必要的独立读回。参见 [测试与证据](../development/TESTING-AND-EVIDENCE.md)。

不要为了文档变更补跑已成功 TASK004 的 Writer。新版部署/恢复详细命令在相应组件的**单独工作**审查，不在 STEP07 生成一套未经实测的万能恢复脚本。
