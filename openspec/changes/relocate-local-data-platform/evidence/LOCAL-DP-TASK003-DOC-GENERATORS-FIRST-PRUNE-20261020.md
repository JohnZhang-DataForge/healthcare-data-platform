# Local DP 4.9 首批历史文档生成器退役（2026-10-20）

> 仅清理三份曾用于写入 2026-10-09 TASK003 冻结文稿的一次性 Bash 文档生成器。**不修改 Synthea、Airflow DAG、Spark、OMOP Writer、SQL、Helm、Secret、镜像或任何持久业务数据。** 是否可合并由当前 PR 的真实 CI 决定；未经测试不记录 PASS。

## 已确认事实及实施范围

- 起始 Main：`b418c1e077be7db21d56f9131709f73fcb0b66b9`；开工时 Healthcare / Self-Runner 最新 Main 分别为 `b418c1e077be7db21d56f9131709f73fcb0b66b9` 和 `4561f666d99e4fe1b014acac65332d5215b0c0c8`。当时没有其他 Healthcare OPEN PR。
- 只删除以下 Git 文件；**保留固定源码 SHA 的只读 Git 历史和原独立 Healthcare-Specs 备份**：

| 退役路径（均位于 `local-data-platform/scripts/task003/`） | 当前源 Blob SHA | 源恢复（冻结原始 Main） |
| --- | --- | --- |
| `04-write-closeout-docs.sh` | `1a3c562dd51456dbe8bd76c1a1a2bb6eafd9cc38` | [原源码](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b418c1e077be7db21d56f9131709f73fcb0b66b9/local-data-platform/scripts/task003/04-write-closeout-docs.sh) |
| `05-write-ae-freeze-doc.sh` | `55fa5b6a48ad15bd66498117856f49decec92ec6` | [原源码](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b418c1e077be7db21d56f9131709f73fcb0b66b9/local-data-platform/scripts/task003/05-write-ae-freeze-doc.sh) |
| `05f2-write-freeze-doc.sh` | `744ff15f6c4df450fd8d4fd4460ec6047c2dca6d` | [原源码](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b418c1e077be7db21d56f9131709f73fcb0b66b9/local-data-platform/scripts/task003/05f2-write-freeze-doc.sh) |

- `04-write-closeout-docs.sh` 使用旧宿主路径 `/data/spark/healthcare-data-platform` 的 `docs/tasks` / `docs/handoffs` / `docs/runbooks`，其生成内容对应历史固定批次；后两个脚本分别将静态验收笔记写到旧 `docs/tasks/TASK-003-STEP05-*.md`，不是运行时业务应用。
- 此前 [第一轮全部两仓 tracked 文件字面消费清点](LOCAL-DP-FIRST-RETIREMENT-CANDIDATES-20261019.md)：Healthcare **622/622**、Self-Runner **270/270**，除自身源码、CODE 导航、审计记录外未见正式 Workflow、DAG、Docker、Spark 等直接引用；后续 2026-10-20 又针对 **86/86** 修改/高优先入口做了有界增量查询，仍无新增直接消费者。**不把文本扫描说成排除所有外部/变量拼接动态使用。**
- 独立备份 [Healthcare-Specs](https://github.com/JohnZhang-DataForge/Healthcare-Specs) 中原 393 文件 SHA/Blob 已核实相同；[增量 395/395 证据](LOCAL-DP-BACKUP-BLOB-READBACK-20261019.md) 另证实后续增量可恢复。
- 对应的新源码运行兼容性已获真实 E2E 核验：2026-10-20 [生成与 S3 READY #39421910846](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39421910846)、[Helm 新 DAG 目录 #39422344924](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422344924)、[Airflow/Spark/OMOP Writer/独立 PG Readback/同 Batch SKIP #39422787433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422787433) 均 **SUCCESS**，没有使用这三个旧文档生成器。以上 **证明核心新链路可以运行，而不代表 4.2–4.4 全量兼容已经关闭**。

## 组件导航和回归门

- 更新 `documents/engineering/development/CODE.md`（2 个退役入口）和 `documents/systems/data-platform/landing/CODE.md`（1 个退役入口），旧链接转为固定 `b418c1e077be7db21d56f9131709f73fcb0b66b9` 历史来源，不再指向 Main 已移除文件；Landing 清单标题 48 → 47。
- 原脚本不执行，不生成旧文档、不触碰 K8s/S3/PG；仅通过 Git 操作删除。
- 合并前要求：适用的 **OpenSpec Change / OpenSpec Static / Docs Links / Component Code Naming / Local DP Source / isolated image build / DAG parse / Writer 安全回归**通过；若失败，定位具体引用或恢复该文件，不能隐瞒失败。
- **不做**另一轮无必要的全仓源码逐文件审计，也**不删除**任何具有活动 Docker COPY、Airflow、Spark、Writer 或恢复价值的文件。

## 未覆盖边界与下一批次

- 这一 PR 只能记为 4.9 **局部历史文件退役**，不代表 Task 4.1/4.8 全量闭包及 4.9/4.10 总体完成；变量拼接、仓库外已冻结 CI 或旧镜像若依赖固定旧源码，应继续指向其冻结 Commit，不允许错误改写为新的 Main。
- 下一批选择有**可证实零业务消费者**的旧生成器/探针，按组件分批处理；保留有价值的测试与受控恢复脚本。历史业务批次不重复执行。
