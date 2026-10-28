# Marquez 公网首版：2026-10-28 UTC 现场观察记录

> **证据级别：USER-SUPPLIED RUNTIME OBSERVATION / PARTIAL ACCEPTANCE，不是完整安全验收。**
> 记录依据为用户在本对话中提供的 `kubectl` / `curl` 输出和 Chrome 公网访问截图；未由仓库 Workflow、独立检查器或本次文档编辑 Session 重新连接共享集群验证。观察窗口约为 **2026-10-28 01:40–02:04 UTC**（美东当地仍为 2026-10-27）。记录时仓库 Main SHA：`eb2330af4ac5ab2c63fbc74e94de4a4c5537501d`，**此 SHA 不是手工部署的源码或镜像构建 SHA**。

## 1. 新增已观察到的运行事实

- **公网地址确实被浏览器访问**：`https://lineage.johnzhang-dataforge.site`。Cloudflare Dashboard 截图显示 `healthcare-marquez-public` 的 Published Application 路由创建成功，`lineage` 的 CNAME 指向该 Tunnel；实际公网浏览器已显示官方 Marquez Web。
- **实机采用的最小链路**：公开浏览器 HTTPS → Cloudflare Tunnel / cloudflared → 同一 K8s Namespace `dw-marquez` 内的独立 Nginx Gateway (`marquez-showcase-gateway`, ClusterIP) → 原有 Marquez Web Service（其自身再代理 Marquez API）→ 原有 PG14。**并未替换原来的 Marquez Web 镜像**，历史内网 `marquez-web-lan` NodePort `30999` 保留。
- **用户已手工建立** `marquez-showcase-nginx` ConfigMap、`marquez-showcase-gateway` Deployment/ClusterIP Service、`marquez-showcase-cloudflared` Deployment 与 `marquez-showcase-tunnel-token` Secret。Gateway Pod 由 `kubectl rollout status` 返回成功，`kubectl get pods` 显示 `1/1 Running`，Gateway Service 为 ClusterIP 80；Cloudflare 公网页面出现说明端到端浏览路径当时可用。**没有收到 cloudflared Pod 的 READY/日志读回**，不据此断言 replicas、连接器高可用或长期健康。
- **仅使用用户本地保管的手工配置**；Nginx YAML、cloudflared YAML、Token、Secret 值、宿主机路径、私网节点 IP、内网访问凭据、部署脚本或镜像二进制 **不纳入仓库**。因此 Git 当前不能单独复现此次手工配置，正式版本仍需另行处理配置恢复、漂移和准入审查。

## 2. 实际 HTTP 响应（通过用户本地 `kubectl port-forward` 测 Gateway）

| 操作 | 用户贴出的返回 | 结论 |
| --- | --- | --- |
| GET `/__healthz` | `200 OK` | Gateway 健康检查 PASS |
| HEAD `/` | `200 OK`、来自原 Web 的 Express 响应头 | 静态 Web 入口 PASS |
| GET `/api/v1/namespaces` | `200 OK`、真实 7 个 Namespace JSON | 核心 GET 代理 PASS |
| POST `/api/v1/lineage`（无业务正文） | `405 Not Allowed` | 此写请求在 Gateway 被拒 PASS |
| DELETE `/api/v1/namespaces` | `405 Not Allowed` | 此写请求在 Gateway 被拒 PASS |
| GET `/api/v1/events/lineage` | `403 Forbidden` | 此未允许路径被拒 PASS |
| GET `/api/v2beta/search/jobs` | `403 Forbidden` | 此未允许路径被拒 PASS |

上述 HTTP 结果**不是**公网黑盒安全扫描、全方法/全路由覆盖测试，也未验证异常 URL、双重编码、路径规范化、GraphQL/admin 管理端点和绕过路线。没有对 PG14/PG17 或 S3 执行写入验证，不推断数据库事务状态。

## 3. 用户 Chrome 公网 GUI 截图验收

| 浏览器功能 | 可证明的范围 |
| --- | --- |
| 官方 Dashboard / Jobs | 公网页面加载真实 Job 卡片，包括 `new_only_omop_consumer` 的 `COMPLETED` 状态，PASS；该状态来自 Marquez 元数据，不替代 PG17 Writer COMMIT 证明 |
| Person 表级血缘 | 在 Spark Business Job 页看到源 Dataset → Person Spark Action Job → Canonical Patient Dataset 连线与双方字段列表，**公网 GUI PASS** |
| Encounter 表级血缘 | 在 Dataset 表级页看到 Dataset 和 Encounter Spark Job 及连接线，**公网 GUI PASS**；此图不能替代完整 Reconcile 双输入同屏全图 |
| **Patient 字段级血缘** | 经 Datasets 列表的 `COLUMN LINEAGE → VIEW` 进入真正独立的 `Column Level` 页面，清楚显示 `ETHNICITY→ethnicity_code`、`BIRTHDATE→birth_date`、`Id→source_record_id`、`DEATHDATE→death_date`、`GENDER→gender_code`、`RACE→race_code` 六条字段连线，**公网 GUI PASS** |
| Encounter 字段级血缘 | 旧 LAN 证据存在；**此次对话未提交其公网 Column Level 截图，公网专项 NOT_CHECKED** |
| Run History / 精确业务提交 | 有 Job 状态可见；公网 Run History 的完整交互、精确 Run UUID 和 PG17 durable COMMIT **本轮 NOT_CHECKED** |
| Dashboard 统计组件 | 初次公网截图出现 `Something went wrong while getting dataset metrics`，统计卡片空白。对应官方前端调用 `/api/v1/stats/{datasets,sources,jobs}`；助手曾提出补充 GET allowlist 的配置建议，**用户没有提交更新后独立读回**，故保持 PARTIAL / NEEDS RETEST |

## 4. 明确的 HOLD / 未验收事项

1. **访问控制未知**：没有匿名无痕窗口/Cloudflare Access Policy 截图或独立访问对照；网站已经通过用户浏览器公开域名访问，但**不能断言只有授权邮箱能看**。在该检查完成前，不应标记为批准匿名公开。
2. **凭据轮换待确认**：早期对话中曾粘贴完整 Tunnel Token，已明确提醒撤销/轮换。此轮没有轮换后 Secret 对应当前 Tunnel 的验证输出；保持 **UNVERIFIED**，绝不上传 Token 或解码原文。
3. **GET 数据披露待审**：官方 Marquez 查询可能包含 Job Facets、SQL、内网对象 URI、运行参数等；界面可见 `SSN`/`PASSPORT` 等**字段名**并不等同于患者实值泄露，但必须核查返回体是否包含敏感信息。GET-only 不代表数据脱敏。
4. **网关安全测试待完成**：当前仅观察到基本 GET/HEAD/POST/DELETE 正反例。M1 精确 UI 请求矩阵、M2 离线攻击负例/默认拒绝安全审计、Gateway 全路径/大小写/编码绕过验证、外网非法方法验证均未完成；内网旧 NodePort 不能成为互联网旁路。
5. **源码/配置未入库**：这次人工临时配置及云端 Token 由用户本地维护；任何未来 Agent 不可因这个记录推断 Git 中已存在正式 Nginx 实现，亦不可擅自用其 PR 覆盖线上手工 Gateway。
6. **UI 只读版尚未独立编译**：公网仍显示原生 Marquez 的按钮；计划后续由 0.51.1 匹配版本源码构建独立 Public Web 镜像，内网 `30999` 原版维持不变。隐藏按钮不是 API 权限边界。
7. **持续在线/公网发布 Gate 未完成**：未检查 Tunnel 连接器持续健康、其他网络设备重现、缓存/CORS/路由全功能或 Cloudflare Access。**即便现场已可访问稳定域名，也不能将 4.2 标为完成**。

## 5. 交接给 M1 / M2 / M3 / 主 Session

- **M1（1.1/1.2）**：以 Marquez 0.51.1 精确 UI 实际调用矩阵为准；特别审查 Dashboard 统计 GET、Events/Search、Dataset/Job/Run Facets 是否适合对外显示。Column Level 是 Datasets 列表最右栏的 `VIEW`，`Mode` 标签不是可点击切换控件。初版实机无定制 UI 也能呈现真实血缘。
- **M2（2.1/2.2）**：将现有用户手工运行 Gateway 当作*需要兼容的 runtime baseline*，不是已并入 Git 的代码或已完成审计的批准实现。离线 Mock + 攻击路径测试后，需经主 Session 审核再决定是否替换手工配置。不能因浏览器已显示图就放宽 API 写入或敏感 GET。
- **M3（3.1）**：Cloudflare Tunnel、CNAME、Published Application 已由用户手工完成；今后的 Runbook 应记录 Kubernetes cloudflared + Secret 方案、访问策略、Token 轮换、受控测试和撤销路线，但不得写入具体凭据、真实私网目标或本地 YAML 源码。
- **Coordinator（3.2/4.1/4.2）**：事实更新为“**公网浏览器已真实加载 Job + Patient/Encounter Table + Patient Column**”；仍保持安全审核和稳定匿名发布 Gate OPEN。下一个最小动作：确认 Access 仅授权账号、Token 已轮换、统计接口和其余 Field/Run 交互、GET 字段披露与公网负向测试。若任一关键检查失败，先在 Cloudflare 停用 route 或停止 cloudflared；不动原内网 Marquez / PG14。
- 当前用户**明确要求仅更新 OpenSpec**，不上传本地 Nginx / cloudflared 源文件，不执行额外 K8s、Cloudflare 或 PG 操作。本记录本身没有新的 runtime 副作用。

**结论：LIVE PUBLIC BROWSER VIEW PROVEN；SECURITY / COMPLETE PUBLIC RELEASE NOT YET ACCEPTED。**
