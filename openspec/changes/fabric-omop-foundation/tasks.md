# Tasks — Fabric OMOP Foundation

## F0 — Warehouse inventory and connection

- [x] 0.1 用户创建现有 Warehouse `dw-omop-5.4` 并提供 SQL Endpoint；后由 Self-Runner 独立 REST 读回目标 GUID，见 0.4。
- [x] 0.2 创建独立 OpenSpec Proposal / Design / Delta Spec / Tasks，冻结与 G5 和 Local DP 的边界。
- [x] 0.3 Self-Runner 已完成受信任 main OIDC REST + SQL SELECT 只读探针，含离线正反测试；PR #483/#484 已合并，静态 CI PASS。
- [x] 0.4 **真实只读连接 PASS**：Self-Runner [Run #41645575691](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41645575691) 完整 SUCCESS，目标 Controller SHA `ef9a0ef224c09a037452e3a9e016a0baf62431e9`；自建 `dw-runner-set` 以 OIDC 执行 Fabric REST 可见性读回；独立托管 Ubuntu 使用相同 Entra SP / ODBC Driver 18 / SQL Audience 执行固定 `SELECT DB_NAME(), CURRENT_USER, 1`。真实 Warehouse Item ID `7a6d08da-278d-4603-8a3b-28640110984c`，`DB_NAME()=dw-omop-5.4`，`SQL_SELECT_PASS=TRUE`。没有运行 DDL/DML/Capacity 操作。
- [x] 0.5 绑定官方 OHDSI CommonDataModel v5.4 固定 Commit / Blob，39 张表、432 字段清单、Fabric 类型适配与 Source-fidelity CI PASS（PR #634/#635）。
- [ ] 0.7 完整 SQL Project / DacFx Schema 迁移、版本升级策略及 Drift Plan 仍须后续独立交付；源文件与首次 CREATE TABLE 不代表已具备 DacFx 升级链路。
- [x] 0.6 已有 Warehouse 首次创建 `cdm` Schema 和 **39 张空 OMOP CDM 5.4 基础表、432 字段**，新建 SQL 连接独立 `INFORMATION_SCHEMA.COLUMNS` 精确读回 PASS；Self-Runner [Run #41648858578](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41648858578)，controller main SHA `d71cab50f25a01b4b245b915b22400f9d99250c6`，Healthcare pinned schema SHA `860af51ca3c1f7389c2276b68494eab274888f94`。
- [ ] 0.8 已创建 `etl`/`audit` 两个 Schema 和 5 张空管理表；**实际 Identity Map 赋值、版本元数据落库、版本升级管线仍未完成**。F1.1b 只证明空表部署，不证明真实临床身份。

## F1 — Independent identity and vocabulary

- [x] 1.1 设计并落地 Fabric-only Identity Map 的 Git SQL 空表结构与源代码测试（不代表云端部署或实际 ID 分配）。
- [x] 1.1a 设计 Fabric-only Identity Map、仓库级 INT 分配器、医院/来源隔离、Ledger 与快照隔离并发 Gate；提出 SQL Schema/CI（代码与设计就绪，不等于已部署）。
- [x] 1.1b **真实部署成功**：`etl`/`audit` 两个 Schema 下 5 张空管理表真实创建，第二条 SQL 连接独立 `INFORMATION_SCHEMA.COLUMNS` 读回匹配且五表全部为空；[Self-Runner Run #41820260817](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820260817) SUCCESS。
- [ ] 1.1c 真正分配稳定 Person/Visit INT IDs、两层唯一性检验、跨医院/跨来源负向和 Replay 验收。
- [x] 1.2 **九张 Vocabulary 文件真实导入 PASS**：Blob 9/9 SHA256，精确字段匹配、源 TSV 解析逐行计数、全部 `COPY INTO` 或严格幂等 SKIP、独立 SQL `COUNT_BIG` 9/9 与源一致，总计 **28,703,753 行**。另外 `concept_id` 唯一性、Concept 日期区间、`vocabulary_id` 唯一性 PASS。Self-Runner [Run #41770643994](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770643994) Completed SUCCESS。
- [ ] 1.3 Vocabulary 深度 DQ 完整收尾（包含正式版本/许可审计）。
- [x] 1.3a **真实跨表引用 DQ PASS**：9/9 表源行数一致，11/11 Concept/Domain/Class/Vocabulary/Relationship/Ancestor/Synonym/Drug 强度引用检查未发现缺失；Relationship reverse 与 Concept 日期有效期亦 PASS。[Self-Runner Run #41820573379](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820573379) SUCCESS。
- [x] 1.3c **真实 F1 元数据 SQL 只读读回 PASS（不等于 1.3b 全部完成）**：[Self-Runner Run #42219030641](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42219030641) 和 [PR #528](https://github.com/JohnZhang-DataForge/Self-Runner/pull/528)，与既有可信 Vocabulary Deep DQ OIDC 和 SQL 身份核对共享通道，真实独立查询 `cdm.vocabulary` 47 行 / `vocabulary_version` 空 28 行、`audit.vocabulary_source_file` 0 行，11 项引用 0 缺失、九表共 28,703,753 行一致。归档审计 `report.json` SHA256 `d822605d00fb7e741b3d7ab7ccf8135f539f499f51fdff73a3343b44662ebb97`、Run Artifact `fabric-p1-f1-metadata-42219030641`。所有读回结果都标记 review-only，未自动批准 clinical/CPT4/license，未持久化来源审计 Manifest 或 Gold。实际缺少的是审计表记录，不是已证实来源 Blob 被删除；`1.3` 和 `1.3b` 仍 OPEN。
- [ ] 1.3b **版本与许可审计仍 OPEN**：`cdm.vocabulary` 47 行中 28 行 `vocabulary_version` 为空，需核查实际 Athena release、CPT4 许可/后处理适用性；`audit.vocabulary_source_file` 目前空表，尚未写入审计 Manifest。不要把 11 项引用 PASS 扩大解释为整个 Vocabulary 版本治理结项。
- [x] 1.3e **Athena 整体版本已核实（仅元数据阶段，不关闭 1.3b）**：Self-Runner [PR #550](https://github.com/JohnZhang-DataForge/Self-Runner/pull/550) / [Run #42322067991](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42322067991) 已真实读回：4,378 字节 `VOCABULARY.csv` 源 Blob 全部字节 SHA256 `795e50e96470e3425556522d15dd99d32a9ddd8044f9e446d9f0e71ee3debd87` 重新计算 PASS，源 47 行与独立 Warehouse SQL 47 行 `vocabulary_id/version/reference` 一一匹配；`vocabulary_id='None'` 的整套词汇 Release 标签为 **`v5.0 27-FEB-26`**。子词汇 CPT4=`2025 Release`，LOINC=`LOINC 2.80`，RxNorm=`RxNorm 20260105`；`CDM v6.0.0` 是 Vocabulary 里 `CDM` 子词汇元数据，不是本仓库目标 OMOP CDM 5.4 物理 Schema 升级。保留 28 个空版本审阅记录（多为内部/分类词汇），未填造。真实 Artifact `fabric-p1-athena-release-42322067991`（ID `13553177319`，ZIP SHA256 `4b18754d135c9abb1164aa6d1e1179cae94dd46276345235f94142dab3d6de27`）。**仍 OPEN**：九文件全量再校验范围、Athena 下载交易/官方来源证明、CPT4 法律授权及必要后处理、`audit.vocabulary_source_file=0/9` 的持久审计、临床审核；不可因此发布 Person/Visit Gold。详见 [统一 FHIR→OMOP OpenSpec P1.4b](../fabric-fhir-omop-unified-e2e/tasks.md)。 OHDSI 官方 [CDM 5.4 Vocabulary](https://ohdsi.github.io/CommonDataModel/cdm54.html#vocabulary) 明确 `None` 标识整套词汇的 Release；该外部规范不替代本轮实机数据证据。


- [x] 1.3f **CPT4 真实 Warehouse 描述完整性聚合审计（限量 SELECT-only）PASS，不等于源文件补全验收**：Self-Runner [PR #592](https://github.com/JohnZhang-DataForge/Self-Runner/pull/592) 合并到 Main `d5c58a9dd4a33da490f4a3102fd0286e22689cf9`；真实 [Run #42448745622](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42448745622)（2026-11-08 UTC）在既有可信 Deep DQ OIDC/Warehouse GUID/SQL DB 身份下，通过两条独立新连接执行固定 `cdm.concept WHERE vocabulary_id='CPT4'` 聚合 SELECT，一致性 PASS。**真实 CPT4 Concept 18,068、空名称 0、名称与 `concept_code` 完全相同 0、已定义常见占位名称 0、1–2 字符极短名称 2**；18,068 与历史约数恰好相等，但不得强制作为其他版本验收条件。Artifact `fabric-p1-cpt4-aggregate-42448745622`（ID `13604337591`）只输出计数、聚合 SHA 与审计状态，不泄露受限术语正文；无 SQL DML、无 Capacity 操作、无 Java/UMLS 调用。**明确剩余：未证明实际执行过 `cpt4.jar` 或当前 `CONCEPT.csv` 为补全后版本，也未证明描述文本逐条准确；CPT4 的下载/使用/公开再分发权、九源同一 release 原始事务、审核时点和 9 条 Audit 持久写入仍 OPEN。** 只核销这一真实只读子项，不关闭 1.3b / 1.6 / 临床 Mapping / Gold。

- [x] 1.5 **F1 治理整改：九文件来源 / 28 个真实原始空版本的统一只读审核工作清单 SOURCE_ONLY**：沿用同一个 Self-Runner `fabric_p1_release_provenance_preflight.py` 与 F1 九文件 `FILES/BLOBS` 和真实 DQ 行数，不复制第二个 Manifest，不重新执行九表 COPY。Self-Runner [PR #591](https://github.com/JohnZhang-DataForge/Self-Runner/pull/591) 已合并 Main `5ccc39fc42261c5fe10481ec10dd8733e1c8d845`；实际 [离线 CI #42440786876](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42440786876) SUCCESS、Artifact `fabric-f1-governance-review-42440786876`（ID `13601137389`），并由原 Vocabulary Deep DQ 离线合同 CI SUCCESS。冻结受信任历史只读 #42219030641（47 SQL 行、28 空 Version、0/9 Audit）、#42322067991（`VOCABULARY.csv` 真实 SHA/47 版本与 SQL 精确对账）、#42313042119（九源 Blob HEAD/长度/ETag），生成无 PHI 的 SOURCE_ONLY `F1_GOVERNANCE_REVIEW_ONLY_HOLD` 差距矩阵：精确列出九缺失 SQL Audit 记录、28 个原始即为空的版本 ID；以**待审查路线而非临床/版权结论**把 `Korean Revenue Code` 与 4 个 `UB04` 项优先列为外部版权/版本核实，其他 23 项列为潜在内部/Type 分类来源审核。工具明确区分**近期只有 VOCABULARY.csv 一份完整字节 SHA 读回、其他 8 个近期只做 HEAD**，不能让冻结 Manifest 或 HEAD 冒充新的 9/9 完整文件核验（历史导入的 9/9 SHA 证据仍成立）。所有输入当前只是**历史物理证据的离线复核**，不声称本轮重新 SQL SELECT、重新 GET 其余源文件、填库、取得 CPT4 或其他许可证；`sql_write_authorized=false`、`license_approved=false`、`clinical_mapping_approved=false`。**1.3b 和 FHIR→OMOP P1.4/P1.5 仍 OPEN。**

- [x] 1.5a **受控九文件来源审计 SQL INSERT 计划已源码化（SOURCE_ONLY，未写入）**：Self-Runner [PR #593](https://github.com/JohnZhang-DataForge/Self-Runner/pull/593) 合并 Main `510a8925bbb5628fd3a612d7b792759d9d73c4ba`，离线 [Run #42449629662](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42449629662) SUCCESS（既有 24 项 Release Provenance + 新增 10 项受控计划正负测试）。基于冻结九文件 SHA/bytes/rows 的同一 Manifest，新增 `prepare_source_audit_insert_review`：要求调用方**实际提供**原始 Athena 下载交易引用和 SHA256，以及九份 `FULL_BYTES_SHA256_VERIFIED` 事件（真实 UTC 完成时间 / Run ID / Controller SHA）；任一缺少即 `F1_SOURCE_AUDIT_INSERT_PLAN_EVIDENCE_HOLD` 且**无 INSERT 参数**。全部是声称值也只产生九组六列 SQL 参数化**审阅计划**，`sql_write_authorized=false`；不连接数据库、不自动设时间、不把 `SOURCE_TSV_VERIFIED` 解析/ETag 日志当全文件 SHA 事件、不从 `v5.0 27-FEB-26` 版本标签推断下载交易或 Release Key。未来需独立源证据审核、准确 Warehouse GUID 与写前 0/9 新连接读回、唯一 Writer Fence、明确持久化授权、单事务与 COMMIT 后 9/9 新连接读回；未知 ACK 只读审查，不能盲目重试。**F1 1.3b/1.6 和 License/Clinical 未关闭，真实 SQL DML 为零。**

- [ ] 1.6 **正式 F1 治理收尾（另行审签/受控写入）**：取得可独立审计的九文件同一 Athena release 原始下载/Manifest 证据、依法使用权与 CPT4/UB04 边界；人工对 28 个源空 Version 的允许空值或补证策略逐条签审，严禁统一伪填版本；冻结真实 `vocabulary_release_key` 和九份可信校验事件时间；在明确写入授权/唯一 Writer/独立 SQL 预检后才可考虑填充现有 `audit.vocabulary_source_file` 六列九条（不得新建重复来源表），未知 ACK 先新连接 GET，写后再独立对账九条 SHA/bytes/rows/release/time。即使真实 Audit 9/9 成功，License / P1 临床 Mapping / F2 Identity / Gold 仍是独立审批门禁。**本次不执行 SQL INSERT 或其他云端写入。**

- [x] 1.4 **F1 来源审计记录与 28 个空版本 ID 审核范围 DESIGN/SOURCE_ONLY**：复用 Self-Runner 已有 `fabric_p1_release_provenance_preflight.py` 固定 SELECT、九文件 `FILES/BLOBS` 原始 pins 和深度 DQ 行数，不建第二套 Manifest 检查器；在 [CDM/Vocabulary 业务文档](../../../documents/systems/azure-fabric/warehouse/CDM54-SCHEMA-AND-VOCABULARY.md) 明确六列 Audit 9/9 单 Release 记录、真实 Blob/SQL 证据、原始 Athena Release/License 独立人工审核、未知 ACK 不重试以及持久写入单独审批/读回。对照 [Run #42219030641](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42219030641) 原始报告精确列出 28 个空版本 `vocabulary_id`；复用 [离线 16/16 Run #42212808029](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42212808029) 与 F1 原实机只读证据。**仅审计方案与审阅队列就绪；`1.3b` release/license 证明、九条审计记录持久写入、临床审核仍 OPEN。**

## F2 — Transactional Gold writer

- [ ] 2.1 实现 Warehouse Writer、Ledger 与原子事务；Person/Visit 真实插入、重放及负向校验（整项仍 OPEN）。
- [x] 2.1a 实现纯 F2 INT ID Preview Planner + Ledger Replay Fence；离线正负向测试覆盖跨医院、同源重跑、冲突、溢出、Snapshot Map/Gold 不一致。**仅 CODE/STATIC，不是实际 Warehouse 分配或 Gold COMMIT。**
- [x] 2.1a.1 **F2 SQL 六表行记录转 Shared IdentitySnapshot 的源码桥接**：沿用唯一 Fabric Writer `writer/silver_identity.py`，对调用方提供的完整真实 SQL 行集按 Self-Runner 已有定序 SHA 算法复算并校验双连接结果、Map/Gold/Allocator 与共享 Snapshot 逻辑指纹；默认只提供 `SOURCE_ONLY_NOT_AUTHENTICATED` Preview。零行时虚拟 next_free=1 仅是首次空 Map 的计算起点，不写入 Warehouse；持久数据却没有 allocator 必须 HOLD。纯合成跨医院/重放/漂移负向测试由原 Warehouse CI 四文件测试集承接。**这不是新实机 SQL 验收，也不关闭 2.1、2.1c 或 P3 Candidate/Gold 的授权门禁。**

- [x] 2.1a.2 **F2 六表真实 SQL 行集→Shared IdentitySnapshot 双连接 PASS；G4 Silver 双 Preview 源码适配 SOURCE_ONLY**：Self-Runner [PR #594](https://github.com/JohnZhang-DataForge/Self-Runner/pull/594) + [PR #595](https://github.com/JohnZhang-DataForge/Self-Runner/pull/595) / 真实 [Run #42466726161](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42466726161)（控制器 `b733d1d071096ff0f4e9226fce64af2d9b1637a2`）完成六表两条独立 SQL 连接及原 Shared 实际源码 Import：六表均 0，physical SHA `0e128f1f9f27f4db42084637da2db9baf74daf03657345788cdff10b133c4890`、Shared SHA `30b218f15d59d11d0105e50d9c42f074536a315b6e6a334f662dcd7e936463ba`，安全 Artifact `fabric-f2-physical-shared-42466726161`（ID `13612340680`）。首次 Run #42466437498 原 F0 SQL 连接 HOLD，二次安全分类后真实 PASS；不跳过 F0。现有唯一 `writer/silver_identity.py` 同路径增量复用 F2 `plan_ids` 与 Shared Preview 校验 G4 Silver 100/5918 的**合成**数据 ID/FK/重跑，非新的 Mapper/Allocator。未实机读取 G4 Silver、未持久化临床身份、未审签 License/Concept；主项 2.1/2.1c 与 P3/P4/P5 Gold 仍 OPEN，实际 SQL DML=NO。


- [x] 2.1a.3 **G4 real OneLake→F2 双读开发及目录异常的独立物理只读预检（验收仍 HOLD）**：Self-Runner [PR #598](https://github.com/JohnZhang-DataForge/Self-Runner/pull/598) 和后续 #599/#600/#601/#602 已合并，复用可信 F0 + 六表 SQL 双连接验证以及 Healthcare 唯一 Shared Engine，新增固定请求和 GUID 下的 G4 Silver Delta Patient/Encounter/Approval 有界 GET-only Reader；不新建 Mapper、Allocator、Warehouse Writer。实际 [Run #42480741491](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42480741491) F0+F2 SQL PASS，但 OneLake 发现 `quarantine` 路径条目；[#42481082624](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42481082624) 得到 `G4_FOREIGN_DELTA_CONTENT_HOLD`。原 G5 [#41636454542](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41636454542) P100/E5918/Q0 为历史 Spark Delta 验收，不表示当前 Source Key GET 已能安全进入 F2。**当前阶段只核销诊断/只读执行源码，无真实 G4 全量身份行集→F2 Preview PASS、无 Gold 写入；2.1/2.1c 与 P3/P4/P5 继续 OPEN。**
- [x] 2.1a.3.1 **真实非预期 OneLake 路径类型确定，元数据诊断 PASS / 业务 Release HOLD**：Self-Runner [PR #603](https://github.com/JohnZhang-DataForge/Self-Runner/pull/603) / [Run #42481611612](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42481611612) 通过可信 Main F0 REST/DB_NAME/六表双 SQL 的原有门禁，固定 OneLake 完整目录 LIST 返回 `G4_FOREIGN_NESTED_QUARANTINE_HOLD`；仅静态类别，未输出目录/源键/内容、未 GET 隔离文件、未触碰 Warehouse/Delta。尚不知该目录是否属于非正式历史工件或含有效 Quarantine Delta Commit，不能以历史 Q0 推出当前对应文件一定无害，2.1/2.1c/P3/P4 主项继续 OPEN。
- [x] 2.1a.3.2 **F2 SQL 通过后的 G4 PathList 格式纠偏证据（元数据实机）**：Self-Runner [Main Run #42483328321](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42483328321) 读取 52 文件、34 Silver / 18 Bronze、六对 Delta V0/后续日志、10 个列表级嵌套 quarantine；全文件树 SHA `174db354bed792a289e002124935010fcc590a14278188f8ce45fa63303751a1`。全部 52 个列表项在旧 Reader 截去请求 ROOT 后还以 `Files` 开头，标准表标签于相对索引 7；不能据此认定真实 Silver 路径嵌套或 Q0 失效。进一步 [HEAD Run #42483902891](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42483902891) 证明三张批准表原始固定 Delta V0 日志 3/3 PRESENT，而重复 ROOT 前缀文件 3/3 MISSING。**源码需严格过滤当前 Approved Processing 范围后再读回数据**，元数据 HEAD≠Delta 内容/身份/Gold Release；2.1 主项仍 OPEN，未执行文件正文 GET 或任何写入。
- [ ] 2.1a.4 **G4 目录异常只读分类及源数据对账后再验收 P2.1**：需精确查明当前 Lakehouse Silver Root 的 `quarantine`/额外文件来源，验证目录归属、真实 Delta Commit/Approval 和完整身份键 FK/Hash；异常仍在时继续 HOLD，禁止伪造 Q0 或绕过业务/许可门禁。

- [x] 2.1b **真实多表事务 ROLLBACK PASS**：Self-Runner [Run #41824079608](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41824079608) 在现有 Fabric DW 验证六张表 BEGIN→合成非 PHI 数据写入→事务内独立行数检查→ROLLBACK→新 SQL 连接六表均为零。实际 SQL SUCCESS，**无 COMMIT、无 Gold 数据持久化**。
- [ ] 2.1c 实现真实单写入者 Gold 事务：重查 Snapshot → Map/Allocator/Person/Visit/Ledger 原子提交 → 独立读回与 Replay。
- [ ] 2.1d 补齐 G5 Candidate 的 hospital_id Join 与真实 Vocabulary Mapping Profile，验证后才允许 F2 clinical writes（包含 2.1d.1 与 2.1d.2）。
- [x] 2.1d.1 修复 G5 Candidate 源码：显式已验证医院 ID + 当前 F1 Warehouse Identity Map 物理字段，跨医院/全局 Person INT 唯一/大小写碰撞负向测试；仅离线 Wheel 0.1.3，不代表 Gold 读写。
- [ ] 2.1d.2 审批真实 Concept Mapping Profile，使用经独立读回的 G4 Silver + Warehouse ID Map/正式 Wheel 实机 Candidate / Gold 集成。

## F3 — Approved G4 to Gold E2E

- [ ] 3.1 使用已批准的 G4 Silver Patient/Encounter，真实 100 Patient / 5,918 Encounter 输入执行并对账。
- [ ] 3.2 独立 SQL readback、DQ/FK/Replay PASS，最后再与 G5 Pipeline 明确集成。

## F0 real execution evidence — 2026-11-03

- [Healthcare OpenSpec PR #632](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/632) merged SHA `99d71e3966bc05183683be5b8637fcb2561f77ec`. OpenSpec validation, Change Gate and link CI PASS; unrelated Workers preview failure was not interpreted as F0 acceptance.
- [Self-Runner probe PR #483](https://github.com/JohnZhang-DataForge/Self-Runner/pull/483) merged SHA `a72932e3f0044e58ae5f08cec94fa35fe8cdd9fe`. First [Run #41645029049](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41645029049) **FAIL** before REST/SQL due `python3 -m pip` unavailable on self-hosted Runner; Warehouse SQL auth was not yet tested. Original failure preserved.
- [Self-Runner fix PR #484](https://github.com/JohnZhang-DataForge/Self-Runner/pull/484) merged SHA `ef9a0ef224c09a037452e3a9e016a0baf62431e9`. Two-stage job: no-pip self-hosted REST + ephemeral hosted ODBC SQL SELECT. [Run #41645575691](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41645575691) completed **SUCCESS**: offline unit tests PASS; REST `FABRIC_WAREHOUSE_REST_VISIBLE=PASS` for exact Warehouse GUID; SQL encrypted TDS `SQL_SELECT_PASS=TRUE`, target DB match, authenticated SP observed. Logs contain no OMOP business rows.
- **Bounded PASS**: Workspace item visibility + SQL connectivity only. **NOT_YET_DONE**: official CDM 5.4 SQL Project, DDL deployment, schema physical readback, Vocabulary, Identity Map, Writer and Gold transactions. These remain explicit tasks 0.5/0.6, F1/F2/F3.

## F0 OHDSI schema-source implementation (design/code, not deployed)

- Official upstream OHDSI `CommonDataModel` pinned commit `b90ae94430e9a266891890a549ac188137fd7f00`, source blob `a77fcad931eef37fe113a79fc266f09cb13e9ed0`; canonical SQL Server 5.4 Base DDL (39 tables, 432 fields).
- SQL source/manifest generated in `azure-fabric/warehouse/omop-cdm-5.4/` with only Fabric-supported type adaptations `datetime`→`datetime2(6)`, `integer`→`int`. An offline PR build verifies fidelity; `0.5` remains OPEN until required CI and reviewed DDL deployment package criteria are satisfied.
- No `CREATE SCHEMA`, no real Warehouse DDL/SQL write, no Vocabulary content or Gold rows have been executed in this schema-source slice. `0.6` remains OPEN.

## F0 source inventory correction — 2026-11-03

- The official OHDSI 5.4 SQL Server DDL contains **39 tables / 432 columns**, including the quoted `note_nlp."offset"` field. Initial manifest/test accidentally counted 431 because the local inventory regex ignored quoted identifiers. This is corrected in the source manifest and tests with unchanged official upstream blob `a77fcad931eef37fe113a79fc266f09cb13e9ed0`.
- Deployment Run [#41647856432](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41647856432) failed at `DDL_COLUMN_INVALID` **before any Warehouse token or SQL write**. Subsequent offline parsing revealed the count mismatch before another cloud deploy. Preserve both diagnostics. DDL source/readback still NOT_DONE at this point.

## F0 verified empty-CDM physical deployment — 2026-11-03

- [Self-Runner PR #485](https://github.com/JohnZhang-DataForge/Self-Runner/pull/485) added first bounded schema deploy. [Initial Run #41647856432](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41647856432) **FAIL** before OIDC/SQL due official `note_nlp."offset"` rejection by local DDL parser; **no Warehouse mutation**. Offline PR verification later revealed the 431-vs-432 manifest error, also before any SQL operation.
- [Healthcare PR #635](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/635) merged SHA `860af51ca3c1f7389c2276b68494eab274888f94` with precise 39-table/432-column source inventory and updated source tests; OHDSI upstream DDL blob itself unchanged.
- [Self-Runner PR #486](https://github.com/JohnZhang-DataForge/Self-Runner/pull/486) merged SHA `d71cab50f25a01b4b245b915b22400f9d99250c6`. PR offline CI fully parses 39 DDL files and validates 432 fields, including quoted `offset`.
- **Real deployment [Run #41648858578](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41648858578) SUCCESS**: exact Warehouse REST item `7a6d08da-278d-4603-8a3b-28640110984c`; SQL identity / Database readback PASS; initial `cdm` was absent with 0 columns; applied `CREATE SCHEMA cdm` and 39 individual `CREATE TABLE` statements (official CDM 5.4 base DDL); reconnected independently with SQL token and verified `CDM54_SCHEMA_READBACK=PASS TABLES=39 COLUMNS=432 EMPTY_DDL_ONLY=YES`. Actual output lists all 39 `CREATED_EMPTY_TABLE` events.
- Runtime scope is **CDM BASE SCHEMA PHYSICAL DEPLOY + READBACK PASS** only. No `etl` / `audit` schema, no PK/FK enforcement guarantee, no Vocabulary data, no ID allocation, no OMOP Person/Visit rows, no Gold transaction, no Spark/FHIR Pipeline execution, no Warehouse re-provision, no Capacity mutation.
- Earlier evidence blocks are historical as of their respective PRs; this live acceptance supersedes only the earlier `schema NOT_DONE` status, not pending F1–F3.

- CI linkage note: this evidence PR uses the existing numeric OpenSpec task `0.6`; follow-up tasks `0.7` and `0.8` remain explicitly open and must not be inferred complete by an empty-table readback.

## F1 Vocabulary Azure Blob → Warehouse execution evidence — 2026-11-03

- Source private container: `johnzhang/omop-vocabulary` (nine root-level files; no GCS/S3/extra Lakehouse). Source verified by [Self-Runner #41768413775](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41768413775): **9/9 exact byte lengths and SHA256 PASS**, OIDC Entra SP direct Blob read PASS. Do not commit raw vocabulary text or CPT4 redistributable content.
- [Self-Runner PR #487](https://github.com/JohnZhang-DataForge/Self-Runner/pull/487) / [Run #41769357041](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41769357041): **readonly F1 preflight PASS**: all nine headers exactly match OHDSI table field order; `FIELDTERMINATOR=0x09`, `ROWTERMINATOR=0x0A` (LF), exact fixed Blob size, nine Warehouse tables empty before first load.
- [Self-Runner PR #488](https://github.com/JohnZhang-DataForge/Self-Runner/pull/488) / [Run #41769826858](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41769826858): **actual Fabric Warehouse COPY INTO PASS** for `cdm.domain=50`, `cdm.concept_class=433`, `cdm.relationship=722`, `cdm.vocabulary=47`. Each row count reconciled with independently streamed source TSV parser; `vocabulary_id` uniqueness PASS.
- [Self-Runner PR #489](https://github.com/JohnZhang-DataForge/Self-Runner/pull/489) / [Run #41770012720](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770012720): deployment switched to **all nine** with immutable storage source ETag, exact row-count replay skip and independent SQL readback. [Run #41770012720](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770012720) loaded **cdm.drug_strength=208,802 rows** and safely skipped the prior four; then held before copying `CONCEPT.csv` due Athena literal-doublequote parse error. [PR #490](https://github.com/JohnZhang-DataForge/Self-Runner/pull/490) proved parser issue at source line 4437, no business data write for CONCEPT. [PR #491](https://github.com/JohnZhang-DataForge/Self-Runner/pull/491) changed CONCEPT and CONCEPT_SYNONYM to literal quote semantics; [Run #41770643994](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770643994) **completed SUCCESS** after the literal-quote fix. Nine-table source row counts and independent SQL readbacks all PASS.
- Warehouse item `7a6d08da-278d-4603-8a3b-28640110984c` already existed and 39 CDM tables were deployed in F0; no DDL or Capacity resume in F1. `etl.identity_map` and OMOP Person/Visit Gold remain NOT_YET_DONE.

## F1 9/9 final physical import acceptance — 2026-11-03 ET

Actual immutable evidence: [Self-Runner Run #41770643994](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770643994), main controller SHA `61c279ffa469028f4b46047acaa34319e64ea970`, exact existing Warehouse GUID `7a6d08da-278d-4603-8a3b-28640110984c`.

| Table under `cdm` | Source rows | Warehouse independent SQL rows | Status |
|---|---:|---:|---|
| domain | 50 | 50 | PASS / replay skip |
| concept_class | 433 | 433 | PASS / replay skip |
| relationship | 722 | 722 | PASS / replay skip |
| vocabulary | 47 | 47 | PASS / replay skip |
| drug_strength | 208,802 | 208,802 | PASS / replay skip |
| concept | 1,952,609 | 1,952,609 | PASS / new COPY |
| concept_ancestor | 10,958,071 | 10,958,071 | PASS / new COPY |
| concept_relationship | 13,150,960 | 13,150,960 | PASS / new COPY |
| concept_synonym | 2,432,059 | 2,432,059 | PASS / new COPY |
| **Total** | **28,703,753** | **28,703,753** | **9/9 PASS** |

- Error correction: original source `CONCEPT.csv` uses literal doublequotes inside medical names. Source parser `csv.QUOTE_NONE` and Fabric Warehouse `FIELDQUOTE='0x08'` are used only on CONCEPT / CONCEPT_SYNONYM. This mirrors established OHDSI Athena import guidance. Previous five successful loads preserved and exact-count replay SKIP validated; no `DROP`, `DELETE`, `TRUNCATE` or duplicate re-import.
- Import performs strict source header checks, OAuth private Blob access, immutable-length + ETag checks, source TSV row counts and Warehouse independent `COUNT_BIG` matches for each table. `CONCEPT_UNIQUENESS_AND_VALIDITY=PASS`, `VOCABULARY_ID_UNIQUENESS=PASS`.
- **Outside the accepted boundary:** CPT4 `CONCEPT_CPT4.csv` name post-processing/licensing (not uploaded to the nine standard tables); Identity Map/ledger; Person/Visit Gold data; semantic FK/Domain and release version audit. These remain separate work and are NOT silently declared complete.

## F1 Identity Map / audit design milestone — 2026-11-04

- F1 Schema source under `azure-fabric/warehouse/omop-foundation/` specifies 5 empty tables across `etl`/`audit`, pinned existing Warehouse GUID. Only code/offline CI in this slice; no cloud DDL or patient data writes.
- Canonical patient source PK `(source_system, source_record_id)`, encounter PK `(source_system, source_encounter_id)`. Add hospital scope to both mappings to prevent tenant collision; use a **global per-entity INT allocator** for Person and Visit within Warehouse, never per-hospital counters.
- Fabric `BIGINT IDENTITY` is incompatible with OHDSI CDM 5.4 `person_id int` and `visit_occurrence_id int`. Stable allocation uses an explicit table and controlled transaction with preflight overflow checks.
- Fabric Warehouse snapshot isolation cannot be overridden with SERIALIZABLE; concurrently allocating from `MAX(id)` without a single-writer gate is unsafe. F2 must enforce single-writer scheduling, detect write conflict and use bounded retry; PK/FK/UNIQUE may be NOT ENFORCED.

## F1 live schema and semantic reference acceptance — 2026-11-04

- [Healthcare PR #643](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/643) merged SHA `195b1f9a387e3393c47cbc298b1110fc34ba52d5`: approved F1 SQL source, 5-table manifest, schema contract, INT identity source-key contract and offline CI PASS.
- [Self-Runner PR #494](https://github.com/JohnZhang-DataForge/Self-Runner/pull/494) merged SHA `c578582df3406b2ba3a45522820656f9db6fbd79`. [Run #41820260817](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820260817) **SUCCESS**: precheck `EMPTY TABLES=5`, actual `CREATE TABLE` five times (`etl.identity_map`, `etl.id_allocator`, `etl.batch_ledger`, `audit.omop_commit_check`, `audit.vocabulary_source_file`), independently read-back schema, five tables all zero rows. NO Person/Visit ID allocation or clinical inserts.
- [Self-Runner PR #492](https://github.com/JohnZhang-DataForge/Self-Runner/pull/492) initial DQ Run #41818140654 failed in client before first count (ODBC cursor timeout misuse); [PR #493](https://github.com/JohnZhang-DataForge/Self-Runner/pull/493) removed unsupported cursor assignment. [PR #495](https://github.com/JohnZhang-DataForge/Self-Runner/pull/495) added bounded progress and triggered [real DQ Run #41820573379](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820573379), **SUCCESS**.
- DQ: nine table COUNT_BIG values exactly match 28,703,753 source rows, all 11 fixed referential checks `UNRESOLVED=0`. `RELATIONSHIP_REVERSE_MISSING=0`, `CONCEPT_INVALID_DATE_RANGE=0`. `VOCABULARY_VERSION_BLANK=28/47` flagged **REVIEW**, not import failure. Semantic linkage PASS does **not** establish license/release validity; no clinical business rows have been committed.


## F2 deterministic Identity/Replay plan — 2026-11-04

- Pure writer planning code lives in `azure-fabric/warehouse/omop-foundation/writer/identity_plan.py`. It **does not** obtain Fabric tokens, insert/allocate durable IDs, operate Spark, or create a Gold receipt.
- Canonical key is `(entity_type,hospital_id,source_system,source_business_key)`. Person Source Key uses G4 canonical `source_record_id`, Encounter uses `source_encounter_id`. Preview IDs positive official CDM 5.4 INT and globally scoped by **entity** in Warehouse, never per-hospital counters.
- Original G5 Candidate mapper requires injected stable `person_id` and still joins source on `(source_system,source_person_id)` without `hospital_id`. This interface mismatch is a **live Gold HOLD**, not a reason to invent a temporary ID. Preview must be revalidated inside a single Warehouse transaction before Map+Person+Visit+Ledger commit.
- Tests cover deterministic order, exact source key replay, hospital namespace separation, casefold/collation collisions, persisted Map/Gold drift, counter rewind/INT overflow, duplicate ledger, conflicting SHA and unverified replay. GitHub CI is source-only; live SQL transaction acceptance is task 2.1b and not yet claimed.


## F2 live transaction rollback rehearsal — 2026-11-04 ET

- [Healthcare PR #645](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/645) merged SHA `ede02cdaf3ff8b41fc39455be387233f538fa8f9`, implements source-only positive INT preview planner and ledger replay negative tests (not a database ID reservation).
- [Self-Runner PR #496](https://github.com/JohnZhang-DataForge/Self-Runner/pull/496) merged SHA `4951bb7cfa0f49d550da727a5838dd3da3eba64d`. [Real Run #41824079608](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41824079608) completed SUCCESS on pinned existing Warehouse: target and DB identity match; all six touched tables empty before run; real Vocabulary Concepts confirmed; synthetic non-PHI rows written inside one explicit transaction to `etl.identity_map` (2), `etl.id_allocator` (2), `etl.batch_ledger` (1), `cdm.person` (1), `cdm.visit_occurrence` (1), `audit.omop_commit_check` (1); `ROLLBACK TRANSACTION` executed; reopened SQL connection independently and verified **zero persisted rows in all six**.
- Explicit scope: actual transaction/rollback behavior verified, not a clinical Gold COMMIT. There was **no** insertion of real G4/FHIR Patients or Encounters, no Capacity resume, no Terraform, and no changes to Vocabulary or Local PostgreSQL. Next is source-scoped G5 hospital join and real Writer Commit/Replay (tasks 2.1c/2.1d).

## F2/G5 hospital identity contract validation — 2026-11-04

- [Healthcare PR #647](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/647) merged SHA `13da96a9bc82463c8be23e3d5f8be385a9655ad4`. [Shared Wheel Offline Validation #41827968535](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41827968535) SUCCESS: 3.11/PySpark 3.5.7 complete synthetic tests and reproducible version **0.1.3** Wheel import; 3.13/PySpark 4.1.1 Spark/OMOP tests plus independent installed Wheel import PASS.
- Explicit batch-authoritative `hospital_id` reconciles the actual canonical v1 `source_system` namespace `raw:hospital:feed`, without changing approved Silver v1 columns. G5 accepts F1 physical Map columns `entity_type/hospital_id/source_system/source_business_key/omop_id`, rejects same-key cross-hospital use, Warehouse-global duplicate Person IDs, case-insensitive collisions, unknown entity and missing source mapping.
- Source-only acceptance. **Fabric Environment 0.1.3 publish/runtime import NOT DONE**, Candidate Delta real write NOT DONE, Gold transaction COMMIT and independent Replay NOT DONE; tasks 2.1c/2.1d.2 remain OPEN.

## G5 Wheel 0.1.3 release prerequisite — 2026-11-04

- [Self-Runner #41833502954](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41833502954) Staging 0.1.3 and [#41834029745](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41834029745) Published 0.1.3 real PASS. No clinical data writes.
- Temporary import-only Spark runtime verification [#41835694167](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41835694167) is a separate open acceptance gate; actual F2 ID allocation, Gold transaction COMMIT and Replay remain open.

### Wheel 0.1.3 isolated live Spark import acceptance — 2026-11-04

- [Self-Runner #41835694167](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41835694167) verified **Completed + exact exit `G5_ENGINE_013_SPARK41_IMPORT_PASS` + temporary Notebook cleanup PASS** after the previously verified Git sync and Publish. The Wheel/Environment prerequisite is **PASS**. Still **NOT DONE**: formal Concept mapping profile, real hospital-scoped Candidate write/readback, F2 Gold Writer `cdm.person` / `cdm.visit_occurrence` COMMIT and idempotent Replay.

## G5 Notebook 0.1.3 source alignment — 2026-11-04

- Source guard in `nb_fhir_ingest.Notebook/notebook-content.py` now matches Shared Wheel `0.1.3` (independently published and imported in earlier real Fabric smoke); offline PySpark dependency and version tests change together. Historic `_G3_PROCESSING` and `_G4_PROCESSING` strings remain immutable (`engine-0.1.1`) so existing Delta paths/replay identities are not rewritten. They identify past publications, **not** the runtime package pin.
- `run_mode = "HALT"`, `write_authorized = False`, DQ/approval/manifest/readback gates and existing physical resource IDs are unchanged. G5 Candidate and F2 Gold writes are **not** enabled.
- Offline CI **is not** real Fabric Git status protection, UpdateFromGit or independent Native Notebook definition readback. Accept only a separate real, fail-closed Self-Runner verification preserving workspace-only items.
- Formal Concept Mapping Profile, stable Warehouse Identity Map allocation, physical G4 100/5918 Candidate Delta, Gold COMMIT and F3 Replay remain **NOT DONE**.

## F2/G5 canonical Silver → Person/Visit identity preview bridge — 2026-11-04

- The pure `writer/silver_identity.py` bridge derives canonical v1 `PERSON` and `VISIT_OCCURRENCE` source keys from independently verified G4 Silver Patient/Encounter rows, requires exact hospital/source/batch namespaces, source FK closure and physical Approval field/count/manifest equality, then invokes the **existing** Warehouse-global INT `plan_ids` logic.
- It emits deterministic `person_id` and `visit_occurrence_id` **proposals** plus visit-to-person ID references. A cross-hospital reused external key must never alias a Warehouse OMOP INT ID. Duplicate/casefold keys, foreign Visit FKs, manifest/count drift, Map/Gold drift and allocator collision/overflow fail closed.
- Status remains `F2_ID_PREVIEW_ONLY_NOT_PERSISTED`: no Warehouse writes, no fabricated Mapping Profile, no official Concept lookup, no fabricated Gold COMMIT / Replay receipt. Physical Approval, Snapshot, mapping and Candidate Delta live readback are separate pending gates.
- The physical Warehouse Identity Map must be updated **only** in the later authorized single-writer transaction with the Person/Visit/Allocator/Ledger COMMIT, not pre-seeded as a disconnected durable map.

## G5 Business Notebook 0.1.3 — real Native Fabric Git acceptance (2026-11-04)

- **Git source:** [Healthcare PR #655](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/655), merged `3923bc35cc2b799051b3d08669250875542ee8d9`. All Notebook Engine guards now require published Wheel `0.1.3`, with default `HALT`, no business write authorization, and historic G3/G4 processing identifiers preserved.
- **Blocker / genuine cause:** [Self-Runner #41849164212](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41849164212) read Fabric Git Status: manually created `dw-omop-5.4` Warehouse, `workspaceChange=Added`, `remoteChange=None`, `conflict=None`. Initial UpdateFromGit correctly HOLD/no write.
- **Protection:** [Self-Runner PR #504](https://github.com/JohnZhang-DataForge/Self-Runner/pull/504) guards exactly Warehouse physical ID `7a6d08da-278d-4603-8a3b-28640110984c`, checks real REST properties and Git status twice before update and again afterward; all unapproved local conflicts still fail closed.
- **First rollout read-only:** [Run #41850613208](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41850613208) returned `ELIGIBLE_OBSERVE_ONLY`, verified canonical Notebook/Pipeline serialization conflict, no errors and `WRITE_ATTEMPTED=False`.
- **Real controlled sync / independent readback:** [Run #41851136478](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41851136478) returned `AUTO_UPDATE_DEPLOYMENT_READBACK_PASS`, `WRITE_ATTEMPTED=True`, `ERROR=NONE`, `notebook_business_cells_match_git=true`, `live_notebook_code_cells=3`, `pipeline_safe_parameters=true`; pinned Warehouse metadata and unchanged local-added status were checked in the same successful run. **GIT_TO_FABRIC_NOTEBOOK_013_DEFINITION_READBACK=PASS**.
- This is **not** an additional 0.1.3 formal-business Spark Runtime execution, Candidate Delta, physical Identity Map persistence, clinical Concept Profile approval, Gold COMMIT or F3 Replay proof. Keep those gates HOLD until separately evidenced.
