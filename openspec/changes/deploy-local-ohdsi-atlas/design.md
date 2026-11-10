# Design — Local OHDSI ATLAS 3.0 / WebAPI 3.0

## 1. Architecture decisions

```text
Browser
  → https://atlas.johnzhang-dataforge.site (USER-CONFIRMED HOSTNAME; DNS/TUNNEL NOT CREATED)
  → Cloudflare Access (email allowlist / deny all nonmembers)
  → existing outbound Cloudflare Tunnel connector (new hostname route only)
  → existing Nginx gateway (inventory before editing)
       /atlas/       → dw-atlas / atlas3-ui internal ClusterIP
       /WebAPI/      → dw-atlas / webapi3 internal ClusterIP
       all other paths → deny or tightly defined redirect
  → WebAPI3 (dedicated service; compatible 3.0.0 release)
       → existing PostgreSQL17 OMOP CDM + Vocabulary (read/select)
       → separate WebAPI application schema + results/temp (narrow read/write)
```

- **不要直接将 Service NodePort、WebAPI、CDM PostgreSQL 或 PG14 公网暴露。** 外部只有 Tunnel 出站；无路由器 inbound port mapping。默认新 Namespace `dw-atlas`，真实名称须先检查碰撞。
- 两条前端路径同一个 Host，避免跨域 OAuth/Access cookie、CORS 和重定向混乱；实际 ATLAS3 的 `base path`/API prefix 由其发行版本测试决定，若官方静态构建只接受根路径，优先保留同域名并通过 Nginx 精确 rewrite（先做离线和浏览器测试），不可凭 2.x URL 假定 3.x path 兼容。
- Cloudflare Access 必须覆盖整个主机名，包括 `/WebAPI/*`；同源 API 请求也必须经过 Access，禁止浏览器 JS 配置绕过 Access 的内网地址。Nginx 防开放代理、限制路径和上传大小、保持 Host/Forwarded/HTTPS；关闭动态 API 的共享缓存与鉴权响应缓存，登录 Cookie 必须 Secure/HttpOnly/SameSite 适当设置。
- **最新实际入口发现**：Self-Runner 受控 GET-only [Run #42735302379](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42735302379) 于 2026-11-09 20:22 ET 实机确认 `dw-marquez/marquez-showcase-gateway` 是 Nginx Deployment，当前在 `worker02`；`marquez-showcase-cloudflared` 在 `worker01`。Gateway/Tunnel 当前来源与历史维护工作可从 Self-Runner PR #337 和相关部署审计追溯；**仍须单独只读核实 Cloudflare 控制台真实 Tunnel hostname、Access 策略、Nginx ConfigMap 的精确配置与当前 Owner**，不得仅凭名称就改写现存 Marquez 路由。

## 2. Versions and source provenance

- OHDSI 官方 [Atlas3 3.0.0](https://github.com/OHDSI/Atlas3) 配套 [WebAPI 3.0.0](https://github.com/OHDSI/WebAPI/releases/tag/v3.0.0)，2026-10-16 首发。WebAPI 3.0 基于 Java21/Spring Boot 3.5，配置形式/数据库迁移与 2.x 不兼容。发布前核实实际稳定镜像仓库、tag、architecture、签名/源代码和 Digest；`latest` 和 `3.0-dev` 不可作为稳定部署锁。
- Broadsea 3.5 常见 Compose 使用 Atlas 2.x/WebAPI 2.x；不能用 Broadsea 快速启动脚本作为 Atlas3 直接部署基础。可以参考 HTTP routing、DB schema 和 source_daimon 配置思想，但必须逐字段适配 3.0。
- 镜像策略：OHDSI Atlas3 3.0.0 的官方 tag 提供 Vue/Caddy Dockerfile，但其公开 Compose 前端使用 `ghcr.io/ohdsi/atlas3:dev`（不可作为正式锁定版本）。先基于上游 `v3.0.0` / 精确 SHA 受控构建静态 UI 镜像并发布至项目 GHCR，锁定最终 digest；不修改/复制上游业务源码。官方 Docker Hub 已提供 `ohdsi/webapi:3.0.0`，先检查多架构版本、完整 digest、默认配置及 plugins；仅当启用 TrexSQL 或其他必须改造内容时才基于上游 pinned Dockerfile 生成项目派生 WebAPI 镜像。不得误用 `ohdsi/atlas:2.15` 与 `ghcr.io/ohdsi/atlas3:dev` 作为生产版本。
- 保留版本矩阵、镜像 Digest、源码 Git tag/commit 和升级测试证据；初次部署 **不从既有 2.x DB 原地升级**，新建/隔离 WebAPI 应用 Schema，并冻结初始化 DDL/迁移状态。

## 3. Database and readiness

**Stage D0：只读 inventory，禁止先 COPY/DDL。**

- PG17 核查实际 DB Name、Schema、表清单和实际行数：`cdm.person`, `cdm.visit_occurrence`, `cdm.observation_period`, `cdm.concept`, `cdm.concept_ancestor`, `cdm.concept_relationship`, `cdm.vocabulary`, `cdm.cdm_source`，及其余官方 39 表/432 列的差异。检查 9 Vocabulary 表、Release、行数、Concept FK 和概念检索索引，核对应用的 PostgreSQL 方言。历史 Local 100 Person / 15,742 Visit 仅代表旧 Run，不是实时 PG 行数。
- Fabric 9 Vocabulary / 28,703,753 是**独立 Warehouse 实体**，不能算本地已就绪。若 PG 缺少 Vocabulary：优先审查既有授权 Athena 来源、许可与当前 Fabric F1 工作中受限制词汇（CPT4/UB04）；取得允许的本地使用证据后，受控导入至本地新建/已审核 schema、逐表读回；绝不直接公开/再分发原词表、自动下载未经授权的内容。
- **WebAPI 应用元数据** 与 **OHDSI Results/Temp** 要求独立命名空间和最小权限；优先在现有 PG17 实例中隔离数据库角色/Schema，减少新的 StatefulSet/PVC。**用户无需提前手工创建新的数据库 PVC、目录或第二套 PostgreSQL**：WebAPI app/meta、accounts、concept-set/cohort-definition 和 Results 是持久化 DB 内容，应纳入 PG17 已有实际备份与恢复范围；实现 PR 审核 DDL/角色后才在 PG17 上创建独立 Schema/DB。具体 WebAPI 3.0 是否允许应用配置 DB 与 CDM/Results 跨 DB 的部署方式，以版本实测为准；如果不兼容，选一个版本匹配、权限隔离且可备份的单实例布局，不能用跨库引用的假设拼凑。
- WebAPI CDM Role 对 `cdm`/Vocabulary 只 SELECT，Results/Temp 只在专属 `atlas_results`/`atlas_temp` 写；WebAPI 应用 schema 独立所有者。任何可能更改 `cdm` 的迁移自动化均须拦截。数据库创建/迁移前：备份、差异/事务/锁影响预检、具名授权和独立结果读回。
- ATLAS3 官方 Compose 的 WebAPI `/data/cache` 是 TrexSQL 插件的**可重建派生缓存**，与上面 PG17 主数据、Cohort Results 区分：MVP 可以先关闭 TrexSQL 或限制 `emptyDir.sizeLimit` 的缓存空间来验收 UI/API、基础 Cohort（官方部分即时 patient-count/inclusion-rule 功能可能不可用），以后确需保留缓存才评估独立小容量 `local-path` PVC（例：5–10Gi 为预算估计，须依据真实占用和现有 StorageClass/worker03 NodeAffinity 确定）。若使用 `emptyDir`，Pod 重启缓存丢失并需重建；不可把缓存当作不需备份的 WebAPI 用户数据。
- Observation Period 缺失时仍可验证 UI、API 和 Concept 搜索，但不得声称完整 cohort/IR 可用；必须先复核观察期定义、Person/Visit FK 与基于合成数据的测试语义，不能仅用所有 Visit 最小/最大日期盲填成研究可用观察区间。

## 4. Authentication/security choice

- **第一层（必须）**：Cloudflare Access Self-hosted Application，精确 allowlist 用户邮箱/身份提供方；所有未授权 UI/API 请求失败，Cookie/JWT 由 Cloudflare 平台管理。用户需在 Dashboard 明确创建 Access 应用与策略，不能以 DNS 记录存在推断 Access 已开启。设置 deny-by-default，验证无 Cookie、未列入用户、URL 编码、不同 HTTP Method 和 API 直接访问。
- **第二层（首选）**：WebAPI 3.0 Spring Security + 最小 RBAC，选择官方支持的 DB Login 或 OIDC 实现；**Access 登录并不会自动成为 ATLAS 登录**。必要时用户出现二次登录，这是可接受的安全行为；若选择一次登录，须单独证实 OIDC 或受支持的身份桥接，不能直接信任客户端注入的邮箱 Header。
- 如果 MVP 暂时只有一名访问者并且无法立即接通 WebAPI 内建登录，则 **Access-only 仅可作为明确审签的短期单用户模式**：Access 限一个邮箱、WebAPI 仅由受保护 Host/私有 NetworkPolicy 到达、不能通过内网其他入口绕过、管理能力均视作高权限；绝不用于多人或匿名公网。未通过外网负向验收 → 保留内网模式，不创建可公开访问路由。
- 绝不使用 Broadsea 的 `admin/admin` 或 `ohdsi/ohdsi` 示例帐号、示例数据库密码；敏感值只能通过既有 Secrets 管理方式，禁止 Git、公开容器配置和浏览器前端泄露。

## 5. Runtime ownership, deployments and limits

- 新源代码/Manifest 计划放在 `local-data-platform/atlas/` 下按功能分组（`kubernetes/`, `config/`, `sql/`），仅在本 Change 的实现 PR 中创建；tests 统一 `.github/quality/tests/data-platform/atlas/`；系统文档在 `documents/systems/data-platform/atlas/`，维护所属 Local DP CODE 导航。不得创建新的源码 README 或重复部署一个 OMOP Mapper/ETL。
- Atlas UI Deployment + WebAPI Deployment 使用 ClusterIP、readiness/liveness probe、受限 ServiceAccount、ResourceQuota/LimitRange、CPU/Memory requests 和合理 job/thread/pool 上限。WebAPI 生成 cohort/分析可写 Results/Temp，但默认不触发昂贵全库扫描；限时/并发、PG statement timeout 和监控不可省略。
- 只读审计现有 PG17 负载、Pool 限额/存储、节点剩余资源、Ingress/Tunnel 的路由策略；避免干扰 Airflow、Spark、Marquez PG14、Local PG Writer 和 Fabric 批次。

### 5.1 Real K8s node placement (2026-11-09 20:22–20:24 ET)

**GET-only physical evidence:** Self-Runner [Run #42735302379](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42735302379) Pod.nodeName/Deployment scheduling/PV affinity PASS；补充 [Run #42735495480](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42735495480) 节点全部工作负载与 requests/allocatable PASS。两个运行均未执行 rollout、patch、apply、Job 或 PostgreSQL DML。

| Node | Label | 现有核心 Pod（只读采集时点） | Requested CPU / allocatable | Requested Mem / allocatable |
| --- | --- | --- | --- | --- |
| worker01 | workload=storage | SeaweedFS 4 Pod、cloudflared、Self-Runner | 1.10 / 5.60 cores | 2118 / 22771 Mi |
| worker02 | workload=platform | Marquez API + 官方 Web + Nginx Gateway、Airflow、Spark Operator | 1.55 / 5.60 cores | 2694 / 22771 Mi |
| worker03 | workload=compute | Local PG17、Marquez PG14、Marquez Public Web、pgAdmin | 1.70 / 5.60 cores | 2642 / 22771 Mi |
| master01 | no workload label | kube-system | 0.90 / 1.60 cores | 70 / 1650 Mi |

各节点 Ready=True；这组值是**资源 requests**，并非 CPU/RAM 实时消耗；`kubectl top nodes` 未提供指标。PG14 `dw-postgre14-data` 的绑定 PV 的 `nodeAffinity` 精确锁定 `worker03`；不可为 ATLAS 隔离而移动/重建此卷。Marquez API/Web/Public Web/Nginx/cloudflared 的 Deployment 均无 `nodeSelector` 和 `affinity`，未来重调度可能改变落点。

**MVP placement decision — user-confirmed worker03 (overrides earlier worker01 recommendation):**

1. `dw-atlas` 的 Atlas3 UI / WebAPI3 Deployment **精确固定在 `worker03`**。先只读确认 `kubernetes.io/hostname=worker03` 和 `workload=compute`、Node Ready/taints、可分配容量及 PG17/PG14 的实际负载；Pod 模板使用 `requiredDuringSchedulingIgnoredDuringExecution` hostname 节点亲和（必要时辅以 compute label）及资源 requests/limits，不能仅用 `workload=compute` 假定以后永远只有 worker03。条件不满足 → Pending/HOLD，不自动放到 worker01/02。
2. `worker03` 现存 `dw-postgre` PG17、`dw-postgre14` PG14、`marquez-public-web`、pgAdmin：**用户选择本机数据邻近并明确接受这些共机事实**。Marquez API/官方 Web/Nginx 在 `worker02`，但四个 Marquez Deployment 当前没有硬 node affinity，后续可能迁移。不得对 Public Web 配置导致 ATLAS 永远 Pending 的硬反亲和；如需防止与 **Marquez 主 API/Web/Nginx** 共机，须基于实机精准标签加选择性 anti-affinity 并证明实际可调度；不得以 Namespace 粗匹配整个 `dw-marquez`。API/Web/Nginx 的长期节点约束属于未来独立授权维护项，不能直接变更。
3. `worker03` 为共用数据库节点，最主要风险是 WebAPI cohort SQL 引发 PG17 CPU/IO/locks/连接数与 PG14 争用；设置 PG connection pool、statement_timeout、WebAPI 工作线程/并发、CPU/Memory 上限和 Results/Temp 存储限额，部署前需真实 CPU/内存/IO/磁盘/数据库压力检查（上表 requests 不是实时 metrics）。无 Metrics Server 可用时采取系统监测/PG 查询等只读替代证据，不可宣称已验证实际空闲。
4. **不移动** PG17/PG14 本地 PV，绝不为了隔离而迁移 Marquez Public Web、改写其 Nginx/Tunnel 或重启已有工作负载；上线后记录所有 Pod 实际 `spec.nodeName`，新增只读漂移检查或告警，说明 `IgnoredDuringExecution` 的限制。

- 不新增 Fabric Capacity 或 Fabric→Local 自动同步。未来 Fabric Warehouse 若要对接 ATLAS/WebAPI 需单独兼容性研究（OHDSI SQLRender、JDBC、cohort SQL、Results 写入）；与本 MVP 无关。

## 6. Stages, acceptance and rollback

1. **D0 INVENTORY_ONLY**：只读表结构、9 Vocabulary 与许可、观察期、资源、Tunnel/Nginx 归属；产出差距报告。禁止把 Fabric 成功数字复制为本地状态。
2. **D1 SOURCE/STATIC**：确认 Atlas3/WebAPI3 匹配稳定版本、锁 Digest、配置/K8s YAML/SQL 迁移预演、单测和恶意路径负向测试；所有代码先在 PR/CI。
3. **D2 PRIVATE_RUNTIME**：获批后初始化独立 App/Results/Temp，WebAPI 严格权限，K8s 内网部署，Private Ingress/port-forward 真实 UI+API 数据源、Concept 查询；任意 DB 修改必须可回滚、独立 SELECT readback。
4. **D3 ACCESS_PROTECTED_PUBLIC**：Cloudflare Access allowlist 生效后，再将新 Host 经现有 Tunnel 指向 Nginx；内外权限负向、ATLAS 登录/登出、Cookie、Host 和 API 路由完整验收。公网未授权 401/403/Access redirect 到登录均视为拒绝，绝不可匿名返回临床源数据/启动 cohort。
5. **D4 ANALYTIC_MVP**：在明确观察期/Vocabulary 完整性和授权前提下，用纯合成患者创建最小 Concept Set、保存 Cohort Definition、生成结果并独立 SQL 读回 Results/Temp，重启后查询一致；如数据缺失则标记 BLOCKED_ANALYTICS，不能将 UI UP 记为业务完成。

**Rollback：** 外网先关闭 Access/新 Tunnel hostname route → 停止独立 ATLAS/WebAPI Deployment → 对新建应用 schema/Results 的回退仅依据独立备份和授权，不执行删除既有 PG17 `cdm.*`、Marquez PG14、SeaweedFS、Airflow/Writer/Identity；保留应用结果用于审计时按受控权限留存，撤销新增 ServiceAccount/Secret 与 NetworkPolicy 只在所有权确认后实施。未知 PG DDL/DML ACK 先独立只读查状态，不盲目重放。

## 7. Non-goals and external documentation

- 不在本 Change 实现新的 Condition/Drug/Measurement、Observation Period 临床语义 Mapper、FHIR/HL7→OMOP Gold、Fabric Writer、Atlas3 内置 PLP 或 ML 模型。
- ATLAS3 3.0.0 **当前未提供**旧版本的内置 Patient-Level Prediction / Population-Level Estimation；后续 ML 使用独立 OMOP Feature/Training Pipeline，不能以 ATLAS 部署成功作为 ML 完成。
- [Atlas/WebAPI 3.0 official release](https://forums.ohdsi.org/t/atlas-webapi-3-0-0-released/26228) · [Atlas3](https://github.com/OHDSI/Atlas3) · [WebAPI release](https://github.com/OHDSI/WebAPI/releases/tag/v3.0.0) · [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/) · [OHDSI CDM source-daemon config](https://github.com/OHDSI/webapi-wiki/blob/master/CDM-Configuration.md).
