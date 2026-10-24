# Local DP 第一批历史源码退役候选 — 三个 TASK003 文档冻结生成器

> **2026-10-19 · 4.1 / 4.8 部分完成，静态消费者负向检查 PASS；不是实际删除批准。** 当前实施规则要求 **4.2–4.4 的兼容性/Build/DAG 门禁先 PASS**，之后才能执行 4.9 的小批量删除。**本 PR 不删除/改名任何业务文件，也不执行它们。**

## 1. 固定输入与完整扫描范围

- Healthcare Main: [`f3b2d9e97d9afe4e7457a1d48fde9e655add47d7`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/f3b2d9e97d9afe4e7457a1d48fde9e655add47d7)；Git Tree 非截断，共 **622** tracked blobs，其中 `local-data-platform/` **393**。Healthcare-Specs private backup: [`6089a2fcf934a26ea0c3fbb8dbdd11bc6f0a42a5`](https://github.com/JohnZhang-DataForge/Healthcare-Specs/tree/6089a2fcf934a26ea0c3fbb8dbdd11bc6f0a42a5)。Self-Runner Main: [`ffd0eccecbf0148183b956e6e4416d4b8d99002b`](https://github.com/JohnZhang-DataForge/Self-Runner/tree/ffd0eccecbf0148183b956e6e4416d4b8d99002b)，Git Tree 非截断，共 **270** tracked blobs。
- 对以上 **622 个 Healthcare 文件和 270 个 Self-Runner 文件**逐个读取 UTF-8 源文本，针对以下三个 Shell 的**精确文件名片段**与三个历史 Markdown 输出文件名进行直接字面引用扫描；这些读取均无错误。本轮静态源码检查的结论不能证明不存在变量拼接、远端工作流调用、已部署容器中引用或仓库外消费者。
- Healthcare 扫描拆分覆盖核对：Local DP 393（TASK003 Shell 94、Tests 105、其余 194），仓库 Workflows 21，文档/Change/入口 75，其他源码/配置 133，合计 **622**。Self-Runner 123 Workflows + 32 CI Script + 115 其他 = **270**。
- `CODE.md` 是源码导航而非当前业务调用链。已存历史证据索引自引用不应误判为运行消费者；对任何将来删除的文件，原文档路径需改为固定历史 Commit 链接，保留审计可读性。

## 2. 第一批具体文件

| 备选脚本（固定 Git Commit） | SHA（目前 Local DP 与独立备份一致） | 实际用途与为何考虑退役 | 仍需维护的非业务链接 | 当前裁定 |
| --- | --- | --- | --- | --- |
| [`04-write-closeout-docs.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/f3b2d9e97d9afe4e7457a1d48fde9e655add47d7/local-data-platform/scripts/task003/04-write-closeout-docs.sh) | `1a3c562dd51456dbe8bd76c1a1a2bb6eafd9cc38` | 历史 STEP04 Closeout 文档、交接、开发经验的生成器，含一次性 Git 源码安装段，非业务运行入口 | [`documents/engineering/development/CODE.md`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/f3b2d9e97d9afe4e7457a1d48fde9e655add47d7/documents/engineering/development/CODE.md) | **C — RECOMMENDED FOR LATER PRUNE / HOLD until 4.2–4.4** |
| [`05-write-ae-freeze-doc.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/f3b2d9e97d9afe4e7457a1d48fde9e655add47d7/local-data-platform/scripts/task003/05-write-ae-freeze-doc.sh) | `55fa5b6a48ad15bd66498117856f49decec92ec6` | 2026-10-09 STEP05A–E 静态验收冻结文档生成器，历史固定数据和路径 | [`documents/systems/data-platform/landing/CODE.md`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/f3b2d9e97d9afe4e7457a1d48fde9e655add47d7/documents/systems/data-platform/landing/CODE.md) | **C — RECOMMENDED FOR LATER PRUNE / HOLD until 4.2–4.4** |
| [`05f2-write-freeze-doc.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/f3b2d9e97d9afe4e7457a1d48fde9e655add47d7/local-data-platform/scripts/task003/05f2-write-freeze-doc.sh) | `744ff15f6c4df450fd8d4fd4460ec6047c2dca6d` | 2026-10-09 STEP05F2 验收冻结文档生成器，历史固定 Run/统计 | [`documents/engineering/development/CODE.md`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/f3b2d9e97d9afe4e7457a1d48fde9e655add47d7/documents/engineering/development/CODE.md) | **C — RECOMMENDED FOR LATER PRUNE / HOLD until 4.2–4.4** |

**关于三个生成器的实际行为**：它们会将旧的 STEP 验收陈述、固定批次、固定 Run ID 或冻结开发记录写到旧工程文档路径 `docs/tasks/`、`docs/handoffs/`、`docs/runbooks/`；不是 Person / Visit / Writer / Spark / Airflow 的生产代码。`04-write-closeout-docs.sh` 还含自复制和 Git 源码更新安装片段。三者都**不能直接运行作为验证**，因为可能在宿主机写入/覆盖历史文件。

## 3. 当前 Git 树证据与负向调用检查

- **现行主线源文件**：对 622 个 tracked 文件直接文本扫描，三个 Shell 文件名出现处仅为：相应脚本自身的历史描述（`04-write-closeout-docs.sh`）、源代码索引 `documents/engineering/development/CODE.md` 与 `documents/systems/data-platform/landing/CODE.md`、OpenSpec 历史文件清单及 TASK003 静态审计矩阵。没有在 21 个当前 Healthcare Workflow、其余 93 个 TASK003 Shell、105 个 Tests、DAG、Dockerfile、App、Spark 或 Terraform/Portal 等其余已检查文件中发现**精确文件名**的直接调用。
- **Self-Runner**：对固定 SHA 的全部 270 个 tracked 文件（含 123 Workflows、32 CI 文件与 115 其他）检查这三个 Shell 的精确文件名和三个旧输出 Markdown 名，均未发现直接字面引用。许多工作流固定在迁移前的 Healthcare SHA，其旧树路径不能因此被“修复”到新 Main。
- **无现行文档产物**：在 Healthcare 当前非截断 Git Tree 中，`docs/tasks/TASK-003-STEP04-CLOSEOUT.md`、`docs/tasks/TASK-003-STEP05-AE-FREEZE.md` 和 `docs/tasks/TASK-003-STEP05F2-CANDIDATE-PREFLIGHT.md` 均不存在；`local-data-platform/docs/tasks/` 亦不是当前受控文档入口。*并不证明未跟踪文件、旧 Runner 工作区或对象存储中没有这些历史内容*。
- **恢复**：当前三个 Git Blob SHA 与 Healthcare-Specs 固定备份 `backup/local-data-platform-20261018-eb216b54/scripts/task003/` 下各对应文件**逐一完全一致**（3/3），且前一轮全局对照 393/393 PASS。删除前仍应复查目标 PR 的最新 HEAD，并确保私有备份长期可访问。

## 4. 剩余门禁和建议的第一轮执行 PR

1. **4.1/4.8 未完成**：确认 README/CODE 所属维护者、历史冻结材料是否应保留为索引链接；对活跃工作流/容器内脚本访问还需动态来源证明。字面模式没有匹配只证明**没有静态精确字符串消费者**，不能排除通用 `scripts/task003/*.sh` 枚举、动态路径组装、旧镜像或不在两仓中的外部调用。
2. **必须先完成 4.2–4.4**：修复现行 Docker Workflow 旧构建路径、生成器双根和关键 Test Root 问题，并通过固定 SHA 静态/单测/Contract/Clean Build/DAG Gates；对本批三文件优先进行直接负向断言，证实主动构建入口无需它们。任何可观察业务改动须另起授权。
3. **未来 4.9 最小删除 PR**：从 Main 仅删除三份 `local-data-platform/scripts/task003/{04-write-closeout-docs.sh,05-write-ae-freeze-doc.sh,05f2-write-freeze-doc.sh}`（一切以 PR 最终 Diff 为准），把两个 CODE.md 中的三条链接改为 [固定 SHA `f3b2d9e97d9a`…](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/f3b2d9e97d9afe4e7457a1d48fde9e655add47d7) 的历史出处；更新适用文档链接/质量测试与固定 SHA 恢复清单。**不**改 Writer/DAG ID、已有任务 SQL、Batch/Manifest/Claim 身份、历史已完成 Run，也不执行历史生成器。
4. **验证/回退**：对新的 PR HEAD 运行 OpenSpec / Documentation Links / Change Gate + 适用的全仓源路径与测试验证；新镜像 Clean Build 和 DAG/Import 由 4.2–4.4 对应步骤负责。失败遵守三轮 HOLD。若有隐性依赖，恢复被删除源文件的精确 Git Blob，不把 Git 回滚当成 PG/S3/K8s 数据回滚。

## 5. 当前门槛状态

| Gate | 结果 |
| --- | --- |
| 622/622 + 270/270 两仓 tracked 源文件的精确文件名静态查询 | **PASS** — 未发现上述三文件的正式入口直接字面调用；自引用、CODE.md、冻结审计记录除外 |
| 3/3 被提名 Shell 当前 Git Blob 与独立备份匹配 | **PASS** |
| 新仓业务 Build、DAG、Spark / 动态模块与容器 provenance | **NOT RUN / OPEN** |
| 通用 Runner / 外部脚本动态文件枚举依赖不存在 | **NOT PROVEN** |
| 三个文件已批准/已删除 | **0 / 0**，明确 HOLD 至 4.2–4.4 |

**结论**：这三个**历史文档生成器**是当前有充分静态证据的第一批 C 类清理优先候选。它们不是必需的业务代码，但只有补完环境兼容和间接消费 Gate 后才能真正从 Main 移除。


## 2026-10-20 有界增量消费者复核（不执行删除）

- 对比原候选筛查 Healthcare SHA `f3b2d9e97d9afe4e7457a1d48fde9e655add47d7` 与当前固定源 SHA `57ce87f866f50f35fc28887c2fbd3675735dd394`，**Local DP 差异仅为两个新增 Quality 文件、两个现有测试修改**；上述三个历史文档 Shell Git Blob **均未变化**。随后到 `addca9ed935b256931b8c67e349639a3f4bb5e9a` 的另一段 Compare：**Local DP 0 文件变化**。原 622/622 + 270/270 静态精确名称扫描保留其**旧固定版本**证据，不冒充今日重跑全量。
- 本轮从固定 Git SHA 直接读取并检查 **26/26 Healthcare 当前 Workflow、8/8 Dockerfile、15/15 Airflow DAG Python、14/14 `scripts/task004/` Shell**（合计 **63/63** 现行高优先级入口），另逐文件读取 Self-Runner 旧基线 `ffd0ecce...` → 已合并 `836ab98d00cb8731b9129fa60a845b8e737efb5d` 的 **23/23** 新增或修改文件（含只读质量 Runner 实现、单测与规范）。
- 在这些 **86/86** 源文件里，针对三个候选脚本的精确文件名、`scripts/task003` 的明显静态路径引用和若干 `find/glob/for` 脚本枚举提示进行有界逐行检查：**没有发现明确的新运行调用链**。与上一轮静态全仓精确名称扫描一起，只能增加其 **C/HOLD 优先候选**的信心；不构成“已证明全仓及容器/外部完全无动态消费者”。例如变量拼接、外部 Runner、已经发布的历史镜像、隐式 Shell 枚举仍属于未知。
- 这三份文档生成器仍保留当前 Git 主线及旧独立备份中，当前 Git Blob 分别为 `1a3c562dd51456dbe8bd76c1a1a2bb6eafd9cc38`、`55fa5b6a48ad15bd66498117856f49decec92ec6`、`744ff15f6c4df450fd8d4fd4460ec6047c2dca6d`。已新增的 [Local DP 395/395 增量源备份核对](LOCAL-DP-BACKUP-BLOB-READBACK-20261019.md) 不改变它们的版本，且只是源码恢复证据。
- **下一 Gate**：检查持久 Docker Build/Workflow 的真正构建路径、调用生成器的动态入口与最小兼容回归；不能拿“没有直接字符串调用”直接授权 Task 4.9 删除。OpenSpec 4.1/4.8 **PARTIAL**、4.9/4.10 **HOLD**；本轮源文件删除、获准删除均 **0**。

## 2026-10-20 首批退役实施结果（覆盖本文历史 HOLD 状态）

这份文件上面的“HOLD / 不执行删除”记录的是 **2026-10-19 之前的静态证据状态**，不是本次实施后的动态任务状态。后来 NEW_ONLY 新目录链路已真实 PASS：[Synthea READY #39421910846](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39421910846)、[Airflow Helm #39422344924](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422344924)、[Spark/原子 Writer/独立 PG/重复 Batch SKIP #39422787433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422787433)。

据此，针对上述三份**仅生成历史 Markdown 文稿**的脚本，已在独立清理分支实施删除及 CODE Map 固定提交链接替换；不重跑冻结文稿脚本，不清理 Spark / Writer 等有效业务源码。首批删除及恢复的具体证据与 PR Gate 见 [2026-10-20 首批退役实施记录](LOCAL-DP-TASK003-DOC-GENERATORS-FIRST-PRUNE-20261020.md)。这只把三个候选由 C/HOLD 推进到“本批待 CI / 合并验收”，**并不代表** 4.1/4.8/4.9 已全量关闭。
