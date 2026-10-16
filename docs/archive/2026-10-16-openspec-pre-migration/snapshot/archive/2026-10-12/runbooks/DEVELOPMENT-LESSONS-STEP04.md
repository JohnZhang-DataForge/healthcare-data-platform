# STEP04 问题复盘与后续开发约定

依据：本阶段实际故障、恢复、重放和 Git 操作记录。

## 1. S3 空列表响应不能只认 KeyCount

现象：Spark 已完成，第 8 段报 `Metadata key exists or S3 listing is invalid`。
实际空列表响应为 `{"RequestCharged": null}`，没有 Contents，也没有 KeyCount。
原检查把缺失 KeyCount 当成非法，误拒绝了本次合法空结果。

修复：明确接受已确认的空响应形态，同时拒绝非空、错误类型、矛盾字段及命令失败。
不能为了兼容而把任意 JSON 对象都视为空列表，也不能把权限或网络错误吞掉后按空目录继续。
该修复已同步 builder 和正式 prepare，测试输出为 11/11 PASS。
后续需核对这些正反例是否全部进入正式 tests；有一次调试 PASS 不等于 Git 中已有持久回归测试。

## 2. 文件写完与产品发布完成是两个状态

本次 data 已存在，但 DQ/manifest 尚未发布。应从这个准确状态恢复。
下游只能消费已批准 manifest 指向的数据；目录存在或 _SUCCESS 存在不能替代发布验收。
发布顺序：data 写入与回读 → DQ 发布与回读 → APPROVED manifest 最后发布。
这个顺序建立消费门禁，不代表多对象存储具备原子事务。

## 3. 恢复已有 run，避免盲目重跑 Spark

恢复前重新核验原 Spark 完成状态、日志标记、TASK-001 血缘、STEP03 结果及 Raw 对象清单。
已有 DQ/manifest 内容一致则复用；内容冲突则停止，不覆盖已发布 metadata。
本次恢复和重放均未重写 Parquet；已有数据得以保留。
将来新实体应复用这套恢复规则，避免每次故障都重新生成 run 或要求人工删目录。

## 4. 幂等必须用重复执行的结果证明

本次第二次 resume 的两项 existing_objects_reused 均为 1，metadata SHA256 不变。
验收记录应包含重复前后状态、对象清单及字段差异，而不仅是程序退出 0。
新 run 全流程成功、同 run 恢复、同 run 重放是不同验收场景，分别记录。

## 5. 正式生成器必须包含修复后的源码

仅修改生成出来的 Python，下一次运行旧 prepare 会把 bug 带回来。
每次修复需要同步生成器，核对生成结果，并保留源码版本或 SHA256。
当前 STEP04 已同步；其他任务的可重建覆盖范围仍需逐项核对。
最终“从零按 Shell 顺序重建”需要干净环境验收，不能仅凭文件齐全宣称完成。

## 6. reset 的边界由真实依赖决定

STEP03/04 的 runtime 文件既是日志，也是血缘和恢复输入。
当前 reset 仅清理 apps/task003、spark/apps/visit、tests/task003 下的 __pycache__。
保留全部报告、数据、稳定 ID、数据库、Kubernetes 资源和旧版基准。
支持 dry-run，实际执行后校验报告 SHA256；以后扩展清理范围应有明确条件。

## 7. Shell 失败传播与输出完整性

- 开启 set -Eeuo pipefail，但仍须核对每个命令的实际失败传播。
- `readarray < <(python ...)` 不会自动把 Python 的退出码当成 readarray 的退出码；关键解析需显式检查生产命令状态和字段数量。
- 关键 S3 查询禁止用 `|| true` 将失败转换为空结果。
- 大段 heredoc 容易在终端粘贴时截断；分段时每段独立校验，完成后再执行正式 runner。
- `bash -n` 只说明语法有效；缺失后续执行段的脚本也可能语法通过。还需验证结构、入口和实际结果。
- BEGIN/END 与退出码必须成对输出；发现缺少 END 应先确认是否分页、仍在运行或粘贴截断。

这些是后续审查规则，不代表现有所有 runner 都已逐项修复并验收。

## 8. Git 登录、提交与分页是不同问题

gh 登录解决访问认证，git user.name/user.email 决定提交身份；本次首次 checkpoint 因缺少身份而停止。
自动化脚本设置 GIT_PAGER=cat，避免 diff --stat 停在分页器的冒号提示。
遇到分页器时按 q 即可继续，不要误判为故障而重跑修改操作。

## 9. 全量替换远程需要明确文件树和历史处理方式

本次先 mirror 备份，再冻结 69 文件快照和远程 main 基线。
保留 smoke DAG 与现有 V2.1 设计；对比增删清单后建立提交。
ours merge 专门用于这次以当前快照替换旧树、连接旧历史的迁移，不是日常解决冲突的通用方法。
正常推送后核对远程 commit 与 tree；远程有并发变化时停止，不擅自 force push。
旧文件仍在历史和备份中；本次操作不等于清除了 Git 历史中的旧内容。

## 10. 后续开发减少重复劳动

- TASK 表示业务任务，STEP 表示任务内部阶段，说明进度时同时写清两者。
- Person/Visit/临床事实表按依赖验收；满足依赖的 Raw 作业将来可由 Airflow 并行运行。
- 复用 manifest、Canonical Gate、publisher、恢复和证据结构；实体差异集中在合同、Adapter 与 Mapper。
- 后续新增功能可逐步提取公共 runner 逻辑，避免不断复制长 Shell；已冻结路径的重构另行回归。
- 每轮交接写明已完成、未完成、证据路径、源码版本与下一条操作。
- 临时脚本编号只是开发过程记录，最终执行顺序应以正式 runbook 和正式 scripts 为准。
