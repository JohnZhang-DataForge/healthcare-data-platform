# Tasks

> **PROPOSED / IMPLEMENTATION NOT AUTHORIZED**：只将旧 Engineering R2–R5 待办转为 OpenSpec 唯一进度来源。R1 新代码功能命名已有长期规则/CI；旧源码目录和文件数量来自 2026-10-16 快照，不能代表当前 Main。

## 1. Governance transfer

- [x] 1.1 核对 [原历史清单](../../../documents/engineering/development/LEGACY-CODE-REFACTOR-PLAN.md) 的静态审计、R1–R5 阶段及受保护的 `task004` 运行身份。
- [x] 1.2 确认本 Change 独立于 [Local DP Path Relocation](../relocate-local-data-platform/tasks.md)，仅记录将来候选实施任务；本次无源码与 Runtime 修改。

## 2. Preconditions — not started / not authorized

- [ ] 2.1 在启动前经用户决定优先级/范围，重新核对最新 Git Main、业务依赖及行为差异，确定所需 Spec 和回滚。
- [ ] 2.2 适用的 `relocate-local-data-platform` Import、Docker、DAG/GitSync、Spark、受控 E2E 兼容验证达到门槛，否则 HOLD。

## 3. Legacy R2–R5 — all pending

- [ ] 3.1 R2 将 Manifest、Plan/Adapter、公共 Validation 按功能封装，证明成功/失败/重复输入等价并保留旧入口。
- [ ] 3.2 R3 调整 Spark reconciliation、Airflow glue，验证 DagBag/Contract/稳定 DAG ID 和必要授权的 Runtime。
- [ ] 3.3 R4 在明确权限后处理 Docker COPY、Base Image、Writer SQL/持久化 PG 接口；保护镜像 Digest、Writer Fencing 与 Batch 身份，禁止盲目重放旧 COMMIT。
- [ ] 3.4 R5 在确认不再有实际依赖后，有界退役旧脚本/模板/测试并保护 Git 历史引用。

## 4. Acceptance / Archive

- [ ] 4.1 每个已实施切片具有准确 SHA、PR/CI、兼容/负向测试和按需独立 Runtime Readback。
- [ ] 4.2 仅在这些步骤真正实施、采用行为需求与长期组件文档同步后归档；不因建立本计划而提前打勾。
