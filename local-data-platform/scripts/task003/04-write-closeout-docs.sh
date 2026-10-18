#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_PAGER=cat

echo "#### STEP04 DOCUMENTATION OUTPUT BEGIN ####"
WORK=""
finish() {
    rc=$?
    trap - EXIT
    if [[ -n "${WORK}" ]]; then
        rm -rf -- "${WORK}"
    fi
    echo "DOC_EXIT_CODE=${rc}"
    echo "#### STEP04 DOCUMENTATION OUTPUT END ####"
    exit "${rc}"
}
trap finish EXIT

ROOT="/data/spark/healthcare-data-platform"
[[ -d "${ROOT}/scripts/task003" ]]

mkdir -p /data/spark/temp_shell
WORK="$(mktemp -d /data/spark/temp_shell/step04-docs.XXXXXX)"

mkdir -p \
    "${WORK}/docs/tasks" \
    "${WORK}/docs/handoffs" \
    "${WORK}/docs/runbooks" \
    "${WORK}/scripts/task003"

cat > "${WORK}/docs/tasks/TASK-003-STEP04-CLOSEOUT.md" <<'DOC_1'
# TASK-003 STEP04 阶段收尾记录

记录日期：2026-10-09。依据：runner01 实际输出、冻结记录及 Git 推送验收。

## 1. 当前结论

TASK-003 的 Canonical Encounter Raw 发布已验收；恢复与同 run 重放通过。
TASK-003 整体尚未完成：OMOP Visit 映射、Processed、Stage、CDM 入库仍待开发。

| 项目 | 已验证结果 |
|---|---|
| TASK-001 整批接收 | 同一批次 18 个 CSV 已完成 Landing 接收和验证 |
| TASK-002 Person V2 | 113 人入库；重复 UPSERT 无新增、无更新 |
| TASK-003 STEP03 | 5799 条 Canonical Encounter，唯一键 5799；Processing readback PASS |
| TASK-003 STEP04 | Canonical Gate、Raw 写入与回读通过；DQ、manifest 发布并回读校验通过 |
| Raw 发布状态 | APPROVED；manifest 最后发布 |
| 同 run 重放 | DQ、manifest 各复用 1 个现有对象，metadata SHA256 不变 |
| 恢复期间 | 未重新提交 Spark；未重写 Raw Parquet；未写 PostgreSQL |
| TASK-003 reset | dry-run 和实际清理通过；Step03/04 报告文件 SHA256 不变 |
| Git | 69 个文件已同步至远程 main；旧历史保留，未 force push |

## 2. 本阶段实际验收路径

1. 原始发布作业完成 Spark Canonical Gate、Raw Parquet 写入和回读。
2. STEP04 第 8 段构建 DQ 时，S3 空列表判断报错，metadata 尚未发布。
3. 只读诊断确认 DQ 和 manifest 目标为空，Raw data 已存在。
4. 修复空列表兼容性判断，同步正式 Python 和正式 prepare Shell；修复测试输出 11/11 PASS。
5. resume 重新核验原 Spark、TASK-001 血缘和 Raw 对象清单，发布 DQ，再发布 APPROVED manifest。
6. 再执行相同 run 的 resume，复用两份 metadata，哈希不变，重放验收通过。
7. 写冻结记录，安装保留证据的 reset，建立并推送源码检查点。

验收边界：修复后没有另建全新 run 重跑完整九段流程；不能将此次恢复验收描述成修复后全流程新 run 验收。
Raw 对象未变化的证据是 key/size/ETag 清单对账，不是逐个 Parquet 对象的字节 SHA256 校验。

## 3. 固化产物

- `scripts/task003/04-prepare-canonical-encounter-publish.sh`：生成本步骤运行源码。
- `scripts/task003/04-publish-canonical-encounter.sh`：新 run 发布入口及 resume 转交入口。
- `scripts/task003/04-resume-canonical-encounter-publish.sh`：已有 run 的 metadata 恢复与复用。
- `apps/task003/build_encounter_raw_evidence.py`：构建发布证据、检查 metadata 目标。
- `apps/task003/resolve_encounter_raw_resume.py`：解析和核验恢复上下文。
- `scripts/task003/00-reset-task003.sh`：仅清理本任务指定范围的 Python 缓存。
- `docs/tasks/TASK-003-STEP04-RAW-PUBLISH.md`：详细冻结记录及源码 SHA256。

prepare 与运行源码已同步；干净环境从零重建尚未验收。
本次增加的文档生成器为 `scripts/task003/04-write-closeout-docs.sh`。

## 4. Git 收尾

- 仓库：`https://github.com/JohnZhang-DataForge/healthcare-data-platform`
- 源码根提交：`1818e05`。
- 已验收远程 main：`e96ec2ae49fe3e7975a94bc7b63a25553257da9a`。
- 已验收文件树：`ad75b3d0a3234bd08e0a59ae353bc821637feb88`。
- 本地仍在 `feature/task-001-synthea-batch-intake`；推送完成时工作区干净。
- 通过 ours merge 连接旧远程历史，文件树使用已审核快照；随后正常推送 main。
- 保留旧 smoke DAG 和 V2.1 设计文档；旧目录文件从 main 新快照移除，旧历史与 stru 分支保留。
- 旧远程镜像备份：`/data/spark/temp_shell/remote-backup.rqLKBp/repository.git`。
- 推送验收：`runtime/work/repo-snapshot.VdDKWI/publish-result.txt`。

69 文件检查点不包含本次新生成的收尾文档和生成器。它们需另外提交；不得声称已包含在 e96ec2a 中。
本地配置、runtime、数据、缓存和 temp_shell 未进入该源码快照；凭据检查是常见模式扫描，不是完整安全审计。

## 5. 后续入口

下一业务目标为 TASK-003 STEP05：Approved Canonical Encounter → OMOP Visit。
交接详见 `docs/handoffs/HANDOFF-2026-10-09-STEP04.md`。
开发经验详见 `docs/runbooks/DEVELOPMENT-LESSONS-STEP04.md`。
DOC_1

cat > "${WORK}/docs/handoffs/HANDOFF-2026-10-09-STEP04.md" <<'DOC_2'
# 开发交接：TASK-003 STEP04 完成，准备 STEP05

交接日期：2026-10-09。本文件描述验收时点，不自动证明未来环境状态。

## 1. 工作方式与边界

- 项目根目录：`/data/spark/healthcare-data-platform`；操作主机：runner01。
- 提供可直接粘贴的 Bash 命令；通过 Shell 生成和修改 Python、YAML、SQL、文档。
- 调试、安装和修复脚本放 `/data/spark/temp_shell`；正式可重建脚本放项目 `scripts/`。
- 已修复内容必须同步正式生成器，不能要求新环境按历史聊天顺序重复打补丁。
- 每一步输出使用 `#### ... OUTPUT BEGIN ####` 与 `#### ... OUTPUT END ####`，退出码由 EXIT trap 输出。
- 每次给出一个可验收步骤，根据真实结果继续；PASS 冻结后不无故重跑或修改。
- `/data/spark/phase3c` 是旧版基准，保持不动。
- 未获凭据时不猜值；不输出 Secret 内容；运行配置不提交 Git。
- 当前协作方式是用户在 runner01 执行命令并回传结果；不要把助手的临时工作区当成 runner01。

运行定位：Spark namespace=`dw-spark`，ServiceAccount=`spark-job`，S3 Secret=`dw-spark-s3-secret`。
S3 endpoint 为 `http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333`。
Spark 镜像、JAR、PVC 和数据库连接方式以正式模板及发现脚本为准；沿用已验收配置，不重新猜测。

## 2. 已完成与未完成

- TASK-001：whole-batch Landing 已验收。
- TASK-002：Person V2 已端到端验收，cdm.person=113。
- TASK-003：STEP03 和 STEP04 已验收；5799 条 Encounter 已进入 APPROVED Raw。
- STEP04 同 run 恢复及重复执行通过，reset 已安装。
- Git main 已同步至 e96ec2a；本地当前分支仍为 feature/task-001-synthea-batch-intake。
- STEP05 尚未实施验收，不能把 Encounter Raw 完成说成 visit_occurrence 入库完成。

## 3. 固定验收定位信息

| 字段 | 值 |
|---|---|
| source / source_version | synthea / v3.3.0 |
| batch_id | synthea-20261005-pop100-atlanta |
| ingest_date | 2026-10-08 |
| Processing run | encounter-20261008T234726Z-1658454 |
| Raw run | encounter-raw-20261009T005128Z-1681690 |
| source_file | payload/csv/encounters.csv |
| source_file_size_bytes | 1883564 |
| source_file_sha256 | 71c7d3fc8dc72c16b33c61c2534c274dcd9f2d96cad102af1554482d69ef7df5 |
| intake_manifest_sha256 | 790409cb0f5f5073d6a94599fcf0e68080216429a9d75b0c89d1a79dc12821e0 |

Raw base URI：

```text
s3://health-raw/canonical_version=v1/entity=encounter/source=synthea/source_version=v3.3.0/ingest_date=2026-10-08/batch_id=synthea-20261005-pop100-atlanta/run_id=encounter-raw-20261009T005128Z-1681690
```

其下正式产物为 `data/`、`dq/result.json`、`manifest.json`。
以上是本次验收定位值；未来 runner 应从已验证状态解析，不能把这些 ID 固定成通用业务参数。

## 4. 必须保留的本地证据

以下路径均相对于项目根目录：

- `runtime/reports/task003/step03/encounter-20261008T234726Z-1658454/run-state.json`
- `runtime/reports/task003/step04/encounter-raw-20261009T005128Z-1681690/run-state.json`
- 同一 Raw run 目录下的 driver.log、SparkApplication、DQ 和 manifest 本地文件。
- `diag-20261009T005543Z-1683198/whole-run.listing.json`：原 Raw 对象清单。
- `resume-20261009T010757Z-1687630/`：第一次恢复成功证据。
- `resume-20261009T011330Z-1689689/`：重复恢复成功证据。
- `replay-check-20261009T011330Z-9iIM2t/`：重放对比和 validation.json。
- `runtime/work/task003-reset-check.SQZpRO/evidence.sha256`：reset 前报告文件哈希清单。

diag/resume/replay 子目录均位于上述 Raw run 报告目录下。
恢复还依赖原 SparkApplication/driver 日志和 TASK-001/STEP03 血缘，不能清理后再假定 resume 可用。
源码仓库不包含这些证据；仅 git clone 不能恢复正在进行中的 run。

## 5. STEP05 开始前需要阅读

1. `spark/contracts/canonical/encounter-v1.json` 与 `spark/contracts/omop/visit-class-v1.json`。
2. `spark/common/omop.py`、Person mapper、Person OMOP SparkApplication 模板和运行脚本。
3. `scripts/task003/01-discover-visit-occurrence.sh`、`02-discover-visit-mapping-foundation.sh` 及可用发现结果。
4. STEP04 正式 manifest、run-state 与现有状态解析代码。
5. 数据库实际 Visit 表、稳定 ID map、约束和词表情况；通过现有访问方式只读核对。

截至本次交接，当前对话尚未收到 e96ec2a 的完整源码包。
已给出 `05a-export-source-context.sh` 导出方式，但没有源码包上传或读取成功证据。
后续可直接读取固定提交，或读取导出的源码包；不要仅凭目录树猜函数接口与数据库 DDL。

## 6. 下一步实施目标

- 从已批准 Raw run 精确读取 Encounter，校验 manifest/DQ/血缘，禁止扫描所有历史 run。
- 复用已验收 Person 稳定 ID；核对 Encounter 的患者关联。
- 依据实际 schema 设计 Visit 稳定 ID 分配，避免重跑时 ID 漂移或碰撞。
- 按版本化合同完成 Visit 类型、日期时间、来源字段等 OMOP 映射；核对词表有效性。
- 通过目标字段、唯一键、Person FK、计数等检查后，发布 OMOP-ready Processed。
- 后续再做 Stage、事务 UPSERT、CDM 对账和幂等验收，不跳过中间验收直接入库。

STEP05 的确切子步骤和 ID map 写入边界，读完现有实现后再确定；当前交接不假定相关 DDL 已创建。
后续本地 MVP 还包括 Condition、Procedure、Drug，以及 Observation 派生 Measurement/Observation，最后加入 Airflow 整批编排和批次汇总。
18 个文件均须有处理结论；不要求本轮把全部 18 个文件映射到 OMOP，非核心文件应明确 DEFERRED。
Azure/Fabric/ML、CI/CD 增强和 FHIR/HL7 接入仍按总设计分阶段推进。
DOC_2

cat > "${WORK}/docs/runbooks/DEVELOPMENT-LESSONS-STEP04.md" <<'DOC_3'
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
DOC_3

cp -- "$(realpath "${BASH_SOURCE[0]}")" \
    "${WORK}/scripts/task003/04-write-closeout-docs.sh"

bash -n "${WORK}/scripts/task003/04-write-closeout-docs.sh"

python3 - "${WORK}" "${ROOT}" <<'PY_INSTALL'
import hashlib
import shutil
import sys
from pathlib import Path

work, root = map(Path, sys.argv[1:])
files = sorted(p for p in work.rglob("*") if p.is_file())

# Check all destinations before creating any final file.
for source in files:
    target = root / source.relative_to(work)
    if target.is_symlink() or (
        target.exists()
        and (
            not target.is_file()
            or target.read_bytes() != source.read_bytes()
        )
    ):
        raise SystemExit(
            "ERROR: existing file differs; preserved: " + str(target)
        )

for source in files:
    target = root / source.relative_to(work)
    target.parent.mkdir(parents=True, exist_ok=True)
    action = "REUSED" if target.exists() else "CREATED"

    if not target.exists():
        shutil.copyfile(source, target)
        target.chmod(0o755 if target.suffix == ".sh" else 0o644)

    print(f"{action}={target}")
    print("SHA256=" + hashlib.sha256(target.read_bytes()).hexdigest())
PY_INSTALL

echo "DOCUMENTS=3"
echo "PERMANENT_GENERATOR=${ROOT}/scripts/task003/04-write-closeout-docs.sh"
echo "DOCUMENTATION_INSTALL=PASS"
echo "GIT_COMMIT_CREATED=NO"
echo "REMOTE_WRITE=NO"
echo "S3_WRITE=NO"
echo "DATABASE_WRITE=NO"
