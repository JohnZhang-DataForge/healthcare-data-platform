# 文档重建与生命周期治理规则 v1

> **历史目录清理**：原 `docs/` 已从 Main 退休；旧验收/Runbook 通过 [固定 Git 快照](../migration/LEGACY-DOCS-SNAPSHOT.md) 读取，不允许新文件写回 `docs/`。所有新增权威项目说明写入 `documents/`；经审核的行为规范与开发变更分别归已初始化的 `openspec/specs/` 与 `openspec/changes/`。

> **状态：ACTIVE · 2026-10-16** · **目标：持续维护准确、可演进、不重复的事实基础；OpenSpec G0–G4 已完成，G5 首个 Change 尚未开始。**

## 1. 基本原则

1. **不是迁移文件，而是迁移经确认的知识**：阅读旧文档只是线索，当前代码/Contract/部署配置和验收证据才是事实核验基础。
2. **单一权威**：每个领域只有一份 ACTIVE 当前解释。跨模块入口只链接不复制 CURRENT/NEXT；不能在多个文件分别保有冲突的状态表。
3. **状态与历史分离**：Current 页面可以覆盖更新；历史 Closeout、GitHub Run、决策、失败事实保持可追溯，不重写成成功。
4. **设计与实现分离**：Target Architecture 与已部署/已验收实现明确标注适用范围和证据，部分上线时允许并存。
5. **渐进式切换**：原 `docs/` 通过固定 Git 历史快照作为 Legacy 参考；某领域经核对及 PR 合并后，才在迁移表标记 `MIGRATED/ACTIVE`。未迁移领域现有有效合同、技术知识和安全规则继续使用。
6. **避免文档膨胀**：同一个 STEP 的小型结果尽量链接 GitHub Run/Artifacts；仅重大变更、独立验收、架构决策保留必要的独立文档。
7. **最小上下文**：新的 Agent 先读 `documents/README.md` 和迁移表，再只读与任务相关的有效文件。

## 2. 最终信息职责

| 类型 | 目标位置 | 权威内容 |
| --- | --- | --- |
| 入口、迁移表 | `documents/README.md`、`documents/engineering/migration/` | 模块导航、迁移状态 |
| Architecture | `documents/architecture/` | 当前系统结构、数据流、设计与部署差异 |
| Systems / Data Platform | `documents/systems/data-platform/<component>/` | 代码路径、依赖、集成方式、实现范围 |
| Engineering / Development | `documents/engineering/development/` | Agent、PR/Self-Runner、测试、文档规则 |
| Engineering / Operations | `documents/engineering/operations/` | 部署、恢复、故障排查、安全操作 |
| Engineering / Status | `documents/engineering/status/` | 少量经证据核对的当前项目与组件状态 |
| Architecture Decisions | `documents/architecture/decisions/` | 重大已批准设计决定、理由、影响和旧方案关系 |
| Evidence | 原 Closeout / GitHub Actions / 已核验的证据索引 | 真实历史验收，不盲目复制日志 |
| OpenSpec（G0–G4 已初始化与集成，业务 Specs/Changes 仍为空） | `openspec/specs/`、`openspec/changes/` | 可测试行为规范和未来 Change 的 Proposal/Design/Tasks |

Azure/Fabric 的唯一当前权威说明位于 `documents/systems/azure-fabric/`，其旧 `documents/components/azure-fabric/` 已退役；Platform Portal 的唯一系统文档入口是 `documents/systems/platform-portal/`，旧 `documents/components/platform-portal/` 已退役。旧 Data Platform、Development、Operations、Migration、Status 的重复副本已从 Main 清理，历史版本仍可通过对应 Git Commit 追溯；任何后续变更只更新新目录。

现有源码中的 `contracts/`、真正运行的 SQL/YAML/Workflow 是实现依据，不因文档重建而移动。

### Component README / CODE 双入口约定

- `documents/systems/data-platform/<component>/README.md`：组件职责、主要数据流、架构边界、当前能力范围和其它权威文档导航；避免在这里重复完整的源码表。
- `documents/systems/data-platform/<component>/CODE.md`：**唯一组件级源码导航入口**，直接链接实际源文件/目录、主要测试、Contract 和构建/部署入口；不复制 CURRENT/NEXT、架构全文或 Runbook。跨组件源码按功能所有权分别登记，不机械复制每个代码目录的 README。
- 原代码目录 README 若只有导航或已有信息，在核对后迁移独有知识、修复所有反向链接、通过路径检查即可逐步删除；不改源码、Runtime、冻结契约或历史证据。
- **Platform Portal 的 README/CODE 收口**：`documents/systems/platform-portal/` 是唯一系统文档入口；Marquez、PostgreSQL14、Airflow OpenLineage、Spark OpenLineage 四个组件各自以 `README.md` 管职责/验收边界，以 `CODE.md` 管真实源码/配置/测试。`platform-portal/` 源码目录不再维护同义 README；真实 Helm、YAML、Shell、Python、CSV 和测试原位保留。新增/删除/移动 Portal 真实源码时，同一个 PR 检查对应 CODE.md；不要混淆 A3/A4 历史分项验收与未批准的 Spark 业务集成，删除 README 不授权部署或 PG14 重装。
- **Azure/Fabric 源码/文档分离**：`documents/systems/azure-fabric/` 是该系统的唯一正式文档入口；`infra-terraform/`、`notebooks/`、`pipelines/` 子组件分别以 `README.md`（职责）和 `CODE.md`（源码）管理。Terraform 详细 IAM/OIDC/Remote State/验收说明集中于 `infra-terraform/ARCHITECTURE.md`。`azure-fabric/` 源码区禁止重复维护说明性 README、CODE 或 ARCHITECTURE；`.tf`、`.tfvars`、JSON、Python 及 Fabric Item 的 `.platform` 等机器可读源码和元数据必须仍放在实际运行源码目录。文档迁移不得改变 Terraform 资源定义、Remote State、Workflow 的部署行为或 Fabric Item 所有权。
- **必须同步**：新增、删除、改名或移动组件源码文件时，**同一个 PR 必须修改对应 CODE.md**，核对导航链接、测试入口和依赖；现有文件的入口/职责/关键依赖改变也必须检查并更新 CODE.md。普通代码内部修改不要求无意义改动，但 Reviewer 需要确认导航未过期。
- **Contract / SQL**：机器可读 Contract、DDL、DML 和只读 SQL 仍是原目录的事实来源，CODE.md 只提供组件所有权导航。SQL 源码地图必须区分只读核验、Rollback 演练、DDL 和 DML；任何导航条目均不代表执行许可。
- **镜像 / Kubernetes**：`images/` 的 Dockerfile/Entrypoint 和 `kubernetes/` 的 YAML / 模板按**工作负载功能所有权**归入组件 CODE.md；RBAC、Secret 引用、持久化资源与镜像 Digest 是实际依赖，不能在文档清理中改动。源目录不能代替 Live Cluster 状态，通用节点/Namespace/存储说明仍由 [Infrastructure](../../architecture/INFRASTRUCTURE.md) 负责。
- **开发脚本和配置**：`scripts/` 的历史 Task-named Shell 按实际业务功能归到已有组件 CODE.md；质量 CI、开发辅助和本地配置示例收口到 [Developer CODE](CODE.md)，不伪造一个新的业务组件。`prepare` 可生成/覆写源码，`reset`/`publish`/`upsert` 等可能改写集群或持久数据；源码导航不是执行授权。新正式 Shell 仍须使用组件名/能力名，不新增 Task/Step 目录。
- **校验**：先对已建立 CODE.md 的组件启用对应静态 CI Gate（已启用 Airflow、apps/、Spark、contracts/、sql/、images/、kubernetes/、scripts/ 与 config/ 的 CODE.md 检查），检查增删/移动时 CODE.md 与 PR 同步，并核对已登记文件存在；各组件逐步启用，不因其它组件暂未迁移而阻止其正常开发。


## 3. 每份新文档的最小元数据

建议使用简短 Markdown Header（无需立即处理所有 Legacy 文件）：

```yaml
---
status: draft  # draft | reviewed | active | superseded
scope: synthea-producer
last_verified: null
source_sha: null
evidence: []
---
```

- `draft`：候选整理，**不覆盖旧有效资料**；`reviewed`：核验完成待采用。
- `active`：已审核并合并到 Main，且迁移表明确该领域的新权威入口。
- `superseded`：已有明确替代路径，不再作为操作依据。
- 对会变的运行环境，`last_verified` 是**核验日期**而非“现在仍然在线”的永久保证；证据须标明环境/时间/范围。
- 不强制每篇写大段 YAML；索引/治理页面可以在正文说明状态。实际业务文档必须能追溯版本和验证范围。

## 4. 模块迁移的固定门槛

1. **Select**：在 [迁移状态](../migration/MIGRATION-STATUS.md) 登记待迁模块、影响范围、Legacy 来源和不迁的历史证据。
2. **Inspect**：按需读取主线代码、Contract、实际部署配置、真实 Closeout/Run；识别已验证、仅计划、已废弃及未知。
3. **Reconcile**：制作冲突决议及事实边界；不采用未经验证的旧 `CURRENT/NEXT`；记录仍有效的安全约束。
4. **Write**：在 `documents/` 模块目录重新组织**简洁且可长期维护**的说明，引用证据，而不是粘贴旧全文。
5. **Review**：进行事实检查、路径/链接检查、PR diff 和受影响 Contract/安全边界审查。
6. **Activate**：合并 PR 后更新迁移表中的领域状态和唯一新权威路径；原 `docs/` 的固定 Git 历史快照可继续作为参考，但不在 Main 维护该领域另一套 CURRENT 状态。
7. **Maintain**：后续相关代码/行为变化触发新文档更新；实施过程与真实结果继续关联版本证据。

若信息不完整或某关键合同冲突未解决，该领域保持 `IN_REVIEW` 而非提前 ACTIVE。拆小 PR 完全允许。

## 5. 日常更新触发与影响

| 变化 | 文档处理 |
| --- | --- |
| 新功能 / 设计调整 | 先说明目标和受影响模块；更新设计及未完成部分；已完成 OpenSpec G0–G4 后按适用的 Change 管理 |
| 新 STEP / Bug 修复 | 仅更新受影响模块、测试与必要状态；不强制新建独立文档 |
| 已验证的功能 / 部署 | 基于 Commit + Run/Readback 更新当前状态和证据索引 |
| 工作流/开发方式改变 | 更新现行 Development 规则，不回写旧验收为新过程 |
| 模块被替换或废弃 | 明确有效范围、替代文档和历史决策；禁用旧操作入口 |
| 失败、回滚、环境异常 | 保存实际证据、风险和恢复条件；不覆盖先前历史事实 |

## 6. Legacy 与历史归档

- 当前 Healthcare `docs/archive/` 已移除；旧归档已被现有文档指向独立 [Healthcare-Specs/archive](https://github.com/JohnZhang-DataForge/Healthcare-Specs/tree/main/archive)（Private，访问按 GitHub 权限），因此**不要根据旧 Lifecycle 文件中的示例重建 `docs/archive/`**。
- 原 `docs/tasks/` 已从 Main 清理；其中 Closeout、冻结 Contract、Runbook 等历史证据仍可通过 [Legacy Docs 固定快照](../migration/LEGACY-DOCS-SNAPSHOT.md) 访问。后续整理不得将这些历史路径描述为当前目录；需要更新证据索引时应先核对来源与可追溯位置。
- 历史文件的正文原则上保持原貌；新解释放在 ACTIVE 文档或迁移说明，修复过期链接时按文件用途审查。
- 本次 Document Rebuild PR 默认 **docs-only、无 K8s/PG/S3/Azure/GitHub Workflow 的运行副作用**。需要 Runtime 验证单独提出并授权。
- 使用 OpenSpec 时，不复制 `documents/systems/data-platform/` 中所有实现说明到 Spec：**Specs 只放可验证行为要求，Docs 放架构/部署/运维知识**。

## 7. PR 最小验收

- 所有修改路径在任务批准范围内；不把未验证事实升级为 ACTIVE。
- 受影响 Markdown 链接可解析；新模块唯一权威路径存在，迁移表与入口一致。
- 说明对应 Main Source SHA、证据来源及尚未覆盖范围。
- 只审核本次 STEP，避免与迁移无关的全仓改动。
- 如发生冲突，记录并解决；无法验证则保持 DRAFT / IN_REVIEW。

## 8. 历史经验与现行规范的边界

- 旧 Skill、历史 Runbook 和故障过程仅在 [Git 历史快照](../migration/LEGACY-DOCS-SNAPSHOT.md) 中查阅，**不作为新的 Agent 执行入口**。不得因为旧文件记载了某项操作，就恢复旧目录、过时状态或 Shell 生成源码流程。
- 现行文档只保留跨任务稳定且会影响开发、安全或验收的工程规则。Shell Parser、Generator、特定路径等零散经验或反复遇到的坑，日后按需另行总结，**不复制进常驻规则**。
- 文档名称保持稳定，语言按实际读者选择；不强制双语副本或语言后缀。重要的历史验收证据仍保留原始 Git/PR/Run 引用，不改写结果。
