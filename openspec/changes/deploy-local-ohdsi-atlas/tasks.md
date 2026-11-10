# Tasks — Local OHDSI ATLAS 3.0 Deployment

> 本轮把 P0/P1 必需项内嵌到 **P2–P4 一次性实施门禁**，不再单独提交一轮冗长调查；OpenSpec 不降低运行时门禁。**本 PR 只有部署源码与只读核查，尚未执行 K8s、PG DDL/DML、Cloudflare、DNS、Tunnel 或 WebAPI 登录。**本 Change 是唯一开发/验收任务清单；任务勾选必须附准确 PR/Run/SHA 和按范围独立读回。

## P0 — Preflight and governance

- [x] 0.1 核查 Healthcare main/开放 PR、当前 Local OMOP Writer/Fabric Vocabulary/Marquez 文档、OpenSpec 与安全规则；确立与正在进行的 Fabric Gold、HL7、Marquez 并行工作互不冲突。此项是 Git/Docs 来源审查，**非实时集群验证**。
- [x] 0.2 对照 OHDSI 2026-10-16 正式版本、ATLAS3↔WebAPI3 兼容边界、Cloudflare Access 外部身份门禁，冻结 MVP 的独立版本与双层网络设计；暂不锁定未核验的容器 Digest。
- [x] 0.3 设计 PR [Healthcare #868](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/868) 7/7 CI SUCCESS、2026-11-09 ET 已合并并实际读回 Main `8646292794e354781c930c23bfa07db69bd035f7`；后续实现均引用 `OpenSpec-Change: deploy-local-ohdsi-atlas` 及具体 Task。
- [ ] 0.4 确定 Self-Runner/本地 Agent 实施入口和当前并行执行者；在任何共享 K8s/PG/Cloudflare 操作前再次核验权限、资源占用和执行授权。
- [x] 0.6 用户确认首发域名 `atlas.johnzhang-dataforge.site`、ATLAS UI/WebAPI 选择 **worker03**（PG17/PG14 所在节点）并采用现有 PG17 存储、非另建 PostgreSQL；这只是设计决策，尚未执行部署或数据操作。
- [x] 0.7 用户指出并已按现有仓库源码布局核实，ATLAS Kubernetes manifests 的唯一正式路径为 `local-data-platform/kubernetes/manifests/atlas/`（既有 OIE、Synthea 位于相同 `kubernetes/manifests/<component>/` 目录）；不得在 `atlas/kubernetes/` 新增平行清单。本次是 OpenSpec 文档纠偏，尚未创建运行资源；以 PR/CI/Main 验证。
- [x] 0.5 **实际节点/角色/资源 requests GET-only 盘点**：Self-Runner [#42735302379](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42735302379) 和 [#42735495480](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42735495480) SUCCESS，确认 worker01=storage（SeaweedFS、cloudflared）、worker02=platform（Marquez API/Web/Nginx）、worker03=compute（PG17、PG14、Public Web），PG14 PV nodeAffinity=worker03。Marquez API/Web/Nginx 当前均无 affinity/nodeSelector，ATLAS 还未部署，节点测量只含 requests 而非实时 top。记录在 design §5.1。
- [x] 0.8 **P2–P4 同轮就绪最小检查**：Self-Runner [#42756234158](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42756234158) GET-only SUCCESS：worker03 Ready、PG17 17.11 在 worker03、OMOP 39 CDM 表、`dw-atlas` 未存在、现有 PG17/PG14 PVC Bound、相关 DB/ATLAS Job 未发现；`concept` 等计数是 pg_class 统计估计，`observation_period` 估计 0，PG17 **备份恢复尚未证实**，未执行任何 K8s/PG 写入。

## P1 — Local PostgreSQL data readiness (READONLY FIRST)

- [ ] 1.1 双连接只读清点 PG17 实际 Schema/39 表/432 列差异、Person/Visit/Observation Period 和九张 Vocabulary 表及统计、source ID 与 FK，留存脱敏报告（**不能**采用 Fabric 28,703,753 替代）。
- [ ] 1.2 核查现有 Athena Vocabulary 使用许可、Release、CPT4/UB04 处理与本地导入适用性；若本地缺失，先提交精确可恢复的补全计划，独立批准后才执行真实导入/读回，绝不再分发受限词项。
- [ ] 1.3 只读确认 PG17 当前负载、存储、连接数、角色以及备份恢复方案；输出精确的 WebAPI app schema、Results/Temp schema 与最小权限 SQL 计划，不触碰 `cdm` 生产业务行；确认现有 PG17 PVC/备份能覆盖新增持久化研究元数据与 Results，**不创建第二个 PG PVC/StatefulSet**。
- [ ] 1.5 真实核查 worker03 CPU/RAM/磁盘/IO/PG17/PG14 压力、实际 Pod nodeName 和存储容量，不以 requests=free/`kubectl top` 不可用代表空闲；在数据库节点设定 WebAPI SQL timeout、connection pool、cohort 并发及资源上限。
- [ ] 1.4 观察期缺失时定义准确 MVP 功能范围和阻断报告；补齐研究级 Observation Period 的规则作为独立业务 Change，不在 ATLAS UI PR 内盲写。

## P2 — ATLAS3/WebAPI3 code and private rollout

- [ ] 2.1 锁定 ATLAS3 3.0.0 上游 tag/SHA 并构建自己的固定 GHCR UI 镜像；检查官方 `ohdsi/webapi:3.0.0` 的镜像 digest、运行配置与必要插件（若需要 TrexSQL 再制作经过审计的派生 WebAPI 镜像）；保存两镜像最终 Digest、Java21/PG兼容性和版本矩阵；拒绝 `latest` / `3.0-dev` / `ohdsi/atlas:2.x` 混配。
- [ ] 2.2 **所有** Local ATLAS3/WebAPI3 的 Namespace、Deployment、Service、ConfigMaps/Secrets refs、ClusterIP、Resource limits、probes、networkpolicy 和调度规则统一新增到 `local-data-platform/kubernetes/manifests/atlas/`；`atlas/config/` 和 `atlas/sql/` 仅容纳应用配置与数据库初始化，不创建 `atlas/kubernetes/`；Image Dockerfile/build contexts 走统一 `local-data-platform/images/`。制定 Nginx 受控路由变更计划，提供离线 Fake upstream/Host/path/未授权 API 测试；不要修改 Marquez Gateway。
- [ ] 2.6 **worker03 硬调度**：ATLAS3/WebAPI3 以 `nodeAffinity.required... kubernetes.io/hostname=worker03` 及实机标签/资源 preflight 固定，PG17/PG14/Public Web **已经**同节点；仅对在 worker02 的 Marquez 主 API/官方 Web/Nginx 做精准选择性隔离/漂移检测，不能对整个 `dw-marquez` 使用硬反亲和，否则 Public Web 导致永远 Pending。worker03 压力过高/节点不 Ready → Pending/HOLD 不自动漂移；负向 CI 拦截错误节点或错误 anti-affinity。
- [ ] 2.7 **长线隔离漂移风险**：评估 Marquez API/Web/Nginx 的对称 nodeAffinity / 只读漂移检测，但须另行授权；用户明确同意 PG14/Public Web 与 ATLAS 在 worker03 共机，不以全部 Marquez 组件分离为验收门槛；禁止擅自移动 PG14 PV 或重启 Marquez。
- [ ] 2.8 **缓存持久化选择**：首版核查 TrexSQL 是否为目标功能所需；若关闭，记录即时 Cohort count/inclusion-rule 的差异；若启用，先评估限量 `emptyDir` 缓存，确有保留价值再单独计划 5–10Gi worker03 绑定可重建缓存 PVC，不将缓存备份与 DB 元数据混淆，且不得手动提前新建未选 StorageClass/PV。
- [ ] 2.9 **一次性 P2→P3→P4 执行**：同一 Session/受控 Runner 依次完成 v3.0.0 pinned GHCR image build/推送及 WebAPI3 digest → PG17 新角色/Schema/Flyway 和独立读回 → `dw-atlas` worker03 私有 Deployment/ClusterIP/真实浏览器 API 调用；每步独立 PASS 才继续，且先核实 PG17 备份、真实 resource usage/磁盘/IO 与非冲突锁。源代码暂在 Healthcare `feature/atlas-p2p4-onepass-20261109`，涉及 `local-data-platform/kubernetes/manifests/atlas/`、`images/atlas3-ui/`、`atlas/config/`、`atlas/sql/`；**源代码验收 ≠ 有副作用执行完成**，不得在尚未有 image Digest、Secret 和实际数据库可恢复证据时自动 `kubectl apply`。
- [ ] 2.3 完成 WebAPI 3 app DB / source_daimon / CDM/Vocabulary/Results/Temp 数据源初始化的**可审计** migration 预检与最小 PG 角色/Statement timeout；先在隔离环境证明只写专属 Schema，绝不无条件自动迁移现有 `cdm.*`。
- [ ] 2.4 获授权后在 `dw-atlas` 内部署，执行真实内网 GET/readiness、UI→WebAPI、真实 Concept 查询和 data source readback；保存 K8s image Digest、Git SHA、Run 证据，失败/未知状态先只读验明。
- [ ] 2.5 在经审批的私有环境实际验证 WebAPI 3 身份/角色管理、未登录 API 401/403、WebAPI 角色不能更新 `cdm`、凭据不出现在 JS/Logs。若采用单用户 Access-only 变体必须写下独立风险决策，不得自动放行外网。

## P3 — Cloudflare / Nginx / protected public release

- [ ] 3.1 Nginx/Cloudflared 的 K8s 实体及落点已在 Run #42735302379 核实（Gateway worker02；Tunnel worker01），**仍需**只读核对其真实 ConfigMap 精确 Host/path、Git/现场唯一 Owner、Cloudflare Dashboard Tunnel/Access/DNS 与 `atlas.johnzhang-dataforge.site` 冲突，因此主项保持 OPEN。用户已确定最终 hostname，不是提议名。
- [ ] 3.2 由具备权限的用户/受控执行者创建 Cloudflare Access Self-hosted Application，精确邮箱 allowlist 默认 DENY；覆盖整个 Atlas Host（包括 /WebAPI），记录应用/策略状态但不记录 Token/PII。
- [ ] 3.3 在前置验证通过后，新增 **仅一个** Tunnel Host→Nginx 路由与对应 path mapping，不新增路由器端口，不破坏 `lineage.johnzhang-dataforge.site`；独立 browser/API GET/POST/OPTIONS、redirect、HTTPS、Cookie/CORS 和无授权否定测试 PASS。
- [ ] 3.4 证明未授权用户无法访问 HTML、静态配置、API、source/sources、运行队列及 cohort；确认没有 NodePort/直达内网 WebAPI 绕过。未通过则撤销新 Host route，保持私有部署。

## P4 — Research acceptance / operational handoff

- [ ] 4.1 在 Vocabulary/Observation Period 数据条件满足时，以少量合成记录实测 Concept Set → Cohort Definition → Cohort generation → Results 独立 PG readback；未满足则保持 ANALYTIC_MVP_BLOCKED，不能写成完成。
- [ ] 4.2 准备独立应用 DB/Results 的备份与可恢复测试、升级/失败回退清单、资源/查询超时、访问日志与最小运维 Runbook；确认不影响 Airflow、Spark、PG17 Writer 和 PG14/Marquez。
- [ ] 4.3 形成浏览器可展示的最终事实：版本、地址、单/双登录行为、公开范围（Access 保护）、真实 OMOP 统计与不可用的临床域；仅在适用的全部运行验收通过后关闭本 Change。
