# Design

## Context

已归档的命名试点 `openspec/changes/archive/2026-10-18-adopt-local-data-platform-naming/` 在迁移前完成，只批准名称。用户随后改变执行顺序：不保留 Main 上双套业务代码，不等待非关键 DAG 完全调试，先独立备份并完成 Main 的物理目录归并，再逐项调试。

以下历史基线与证据均由 GitHub 的真实仓库、PR/Run 和 Git Tree 核对；此 Change 的建立日期晚于 PR #225–#227 的合并，**不是预先获准实施的证据**。

## Decision

### 1. 源码及独立备份

- 源仓库：`JohnZhang-DataForge/healthcare-data-platform`，搬迁前固定 Main SHA `eb216b544381ab0e73bd221cd54d8887f77b9a10`。
- 待搬业务源码：`apps/`（66）、`airflow/`（15）、`config/`（1）、`contracts/`（5）、`images/`（10）、`kubernetes/`（11）、`scripts/`（123，不含 quality）、`spark/`（44）、`sql/`（13）、`tests/`（105，不含 quality）；合计 **393 个 tracked 文件**。
- 独立备份：私有仓库 `JohnZhang-DataForge/Healthcare-Specs` 的 `backup/local-data-platform-20261018-eb216b54/`，包括原目录结构、`SOURCE-BLOBS.tsv` 和恢复说明；PR #2 已合并 Main SHA `6089a2fcf934a26ea0c3fbb8dbdd11bc6f0a42a5`。通过逐个 Git Blob SHA readback 校验 **393/393 一致、0 不一致**。备份不位于新源码构建工作树内，且不构成 K8s/数据库快照。
- 搬迁分支曾先复制 393 文件，核对 SHA，再从**迁移分支**移除旧根目录；此前的 Main 保持不变，直至 PR #225 合并。GitHub PR #225 合并后旧业务根路径文件数为 0。

### 2. 当前权威目录结构

```text
healthcare-data-platform/
├── .github/
│   ├── workflows/
│   └── quality/
│       ├── scripts/              # 3 个全仓质量检查器
│       └── tests/                # 3 个全仓质量单元测试
├── local-data-platform/
│   ├── apps/
│   ├── airflow/
│   ├── config/
│   ├── contracts/
│   ├── images/
│   ├── kubernetes/
│   ├── scripts/
│   ├── spark/
│   ├── sql/
│   └── tests/
├── azure-fabric/
├── platform-portal/
├── documents/
│   └── systems/data-platform/    # 仍为组件文档命名空间
├── openspec/
├── AGENTS.md
└── README.md
```

保留 Azure/Fabric、Portal、文档、OpenSpec 和仓库级自动化的独立所有权；不得将 `documents/systems/data-platform/` 改名以迁就代码路径。

### 3. 历史实施及实际检查

| 记录 | 实际完成的边界 | 证据 / 局限 |
| --- | --- | --- |
| Healthcare-Specs PR #2 | 备份 393 个原始文件到私有仓库 Main，原始 Blob 一致 | Backup Run [#39158372198](https://github.com/JohnZhang-DataForge/Healthcare-Specs/actions/runs/39158372198) SUCCESS；源 Main `eb216b54...`，备份 Main `6089a2fc...` |
| Healthcare PR #225 | 393 个本地业务文件进入 `local-data-platform/`，删除旧根业务路径 | PR HEAD `46018cca30d9669d0400a826cdaf0c069033095f`，Main Merge `377df7c9fae770cde985f6e7bcbc47d40ecfa355`；[OpenSpec Run #39160915519](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39160915519) SUCCESS，但 [Component Naming Run #39160915562](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39160915562) **FAIL**（旧 CODE Map），用户接受目录切换优先；不算全绿 |
| Healthcare PR #226 | 修复有效文档源码链接和 CODE Map 识别（不改业务代码） | HEAD `67085d1bb0d99200c093a2edff3b39690a32ec15`，Merge `3af772f60c8ce5aac6f474cf8b291b13d82d3d88`；[Docs Run #39162992543](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39162992543)、[Component Run #39162992540](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39162992540)、[OpenSpec Run #39162992541](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39162992541) SUCCESS；当时 Markdown 链接 1,034 / missing 0 |
| Healthcare PR #227 | 6 个全仓质量文件迁入 `.github/quality/`，更新 CI/Import/导航；根目录无 `scripts/`、`tests/` | HEAD `48f587840a08174d98c1e3c15876b4ba2b1962f0`，Merge/Main `7e969718cfad9368fd13866053636c787e24ca7e`；[Docs Run #39163725180](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39163725180)、[Component Run #39163725249](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39163725249)、[OpenSpec Run #39163725294](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39163725294) SUCCESS；38 质量单测、1,035 文档链接 / missing 0、CODE Map PASS |

原 #225 已完成的物理搬迁不可解释为 **G6 全套运行验收已完成**。历史 PASS 不跨 SHA、环境和构建镜像 Digest 自动继承。之前的 OpenSpec CI 可在 0 Active Changes / 0 Current Specs 时通过，只代表 CLI 配置/已有文件通过格式验证，未强制 PR 关联 Change。

### 4. 后续运行兼容与逐层调试（待实施）

1. 建立所有仍指向旧源码根目录的静态引用清单：Python Imports、`PYTHONPATH`、Runtime `PROJECT_ROOT`、脚本、Docker `COPY`/build context、镜像生成器、GitHub Actions/Self-Runner、Airflow GitSync DAG 目录、SparkApplication 路径、非 Markdown 配置。保持旧 DAG ID、Batch 身份、Manifest 和数据存储路径，除非后续 Change 明确授权修改。
2. 静态/单测/Contract 在准确 Commit SHA 上逐项 PASS；添加 **无旧路径/旧安装包可导入**的负向证明，防止误用旧来源。Docker 镜像应在干净环境中构建和检查 module `__file__`、Digest；镜像 Build 不能等于真实数据库写入。
3. 使用受控隔离测试依赖重演 NEW_ONLY Person/Visit 路线：生成、Landing/Manifest、DAG、Spark、OMOP Writer/PG 独立读回和重试 SKIP；冻结输入并比较业务键、行数、契约、Fingerprint，运行时间与随机元信息不能充当业务回归比较依据。
4. 共享 K8s/PG/S3/Airflow 的任何写操作、真实调度/部署或历史 Batch 回放前需要单次明确授权、资源协调与 Writer Fencing 安全检查。不得以先前用户同意非关键 DAG 暂时中断代替后续共享环境写入授权。
5. 调试每同一问题最多三次尝试；未知结果、冲突、Writer UNKNOWN、不可重复的已完成 Batch = HOLD 并记录 PR/HEAD/Run/症状与安全 Next。
6. 实际源码/运行验收之后才更新 Current Specs（如行为有可证明变更）和 Archive；当前 `skip_specs: true` 因此 Change 只跟踪路径结构与不变性要求。

### 5. 回退边界

- 源码：由独立 Git 备份与固定 SHA 恢复；不将历史源码重放到生产部署视为自动安全操作。
- 镜像：需要明确发布的 Digest、所选 DAG/构建入口及对应 SHA，不能只依赖 mutable tag。
- 数据：没有迁移 DB/S3 中的数据；恢复 Git 目录不能撤销 PostgreSQL DML、K8s Job 或已完成批次。禁止未经审计重放历史成功 Writer Batch。
- 文档事实与治理：修复项目状态中关于“代码尚未搬迁”的过时说法，但不重写旧验收、旧 PR/G3 历史证据。下一轮才设计强制 OpenSpec Change Gate、分支保护与 PR 映射；本 Change 不改变这些策略。

## Verification & Archive Gate

- 本追溯记录 PR 在**准确 HEAD** 上通过官方 OpenSpec Strict Validation、Markdown Relative Links 及适用 CI；对既存 PR 和备份标出实际 SUCCESS/FAIL。
- 可以合并此事后追溯 Change，但 **不得在运行路径与回归验收未完成前 Archive**。
- 后续每个实施 PR 引用同一 Change ID 与待办项；未来治理 Gate 应另建 Change，不能将这轮 PR 当成 Gate 已存在的证据。
