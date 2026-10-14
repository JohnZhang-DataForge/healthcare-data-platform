# Marquez + PostgreSQL14 部署尝试：三轮停止 / 安全交接（2026-10-13 EDT）

> **结果：PARTIAL / NOT DEPLOYED。** 根据用户要求，同一轮失败尝试达到三次即停止。**绝不声称 Helm 安装、Marquez API、Web UI、Schema Migration 或 NodePort 30999 已完成。** 本文是尝试记录，不是部署成功 Closeout。

## 1. 目标和固定边界

- Marquez namespace：`dw-marquez`（此前路线 A 明确选定；不使用旧提案 `dw-demo`）。
- 独立已存在 PostgreSQL：`dw-postgre14/dw-postgre14-database-0`，DB/role `marquez`，PostgreSQL **14.24**，Service `dw-postgre14.dw-postgre14.svc.cluster.local:5432`。
- 保留原有独立 `postgres-marquez` Retain PV/PVC；禁止创建/重装或删除 PostgreSQL14。
- PostgreSQL17 `dw-postgre`（OMOP/Airflow）、Synthea、SeaweedFS、Claim、Writer **均未更改**。
- 目标 Chart：官方 Marquez `0.51.1`，从 annotated tag 对应 commit `27a4a1357d9078bc4e6738524dfe5ba9d77aa2df` 获取源码 `chart/`，不使用不存在的官方 Helm HTTP Index；Helm pin `v3.17.3`、校验 sha256。
- 目标网络：Marquez API 和 Web upstream Service `ClusterIP`；单独 `marquez-web-lan` Service `NodePort:30999` **仅在后端和 Web 都真正 Ready 后再创建**。Web Proxy 可访问 API；非经 LAN/VPN/NAT 安全核查不得视为公网安全。

## 2. 三轮真实运行结果（Self-Runner）

| Run | 状态 | 真实阻塞 | 影响 |
| --- | --- | --- | --- |
| [38497221548](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497221548) | FAILED | `helm: command not found`（Runner 缺 Helm） | Checkout 阶段停止；未创建任何 Marquez/K8s/DB 对象 |
| [38497309444](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497309444) | FAILED | Helm v3.17.3 checksum 安装 PASS，PG14 实测 preflight PASS；错误 Helm repo index URL 404 | 已创建 `dw-marquez` namespace，以及 `dw-marquez/marquez-db` Secret（密码经 Runner stdin 从 PG14 原 Secret 复制，**未打印和未存仓库**）；无 Marquez Deployment / Helm release / DB migration |
| [38497455412](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497455412) | FAILED | 部署脚本更新 GitHub 源码下载方式时发生一次文本替换错误：`line 64: POSTGRES_USER: unbound variable` | PG14 preflight、端口和 Secret 检查再次 PASS；在 Chart 渲染或安装前停止；既有 namespace/Secret 被安全复用 |

**三轮均未运行到 `helm upgrade --install`；没有创建 API/Web Pods，没有 Marquez 元数据表，没有 S3/API 事件，也没有开放 `30999`。** 不得把 `PG14_ISOLATED_DATABASE_PREFLIGHT=PASS` 写成 Marquez 运行成功。

## 3. 代码修复与当前仓库状态

- Healthcare Feature Branch：`feature/marquez-pg14-api-web-20261013`。
- 两份正式代码：
  - `kubernetes/marquez/values-pg14.yaml`：仅 host/database/user、Chart resources 等**非秘密**配置，postgresql chart disabled，service.type=ClusterIP。
  - `kubernetes/marquez/deploy-pg14.sh`：逐项 preflight、只在缺少时创建 Namespace/Secret、下载官方 tagged **commit** 的 chart、Helm 依赖构建、独立 API/Web + schema 验证、最后 Web-only NodePort。
- 第三轮失败后，已**从首次未损坏的固定文件版本重新构造脚本并修正文本替换机制**，当前修复提交为 `6a2849f24eee2b87bd95cb1292efcaccf74780ae`。**修复仅作为候选源代码保存，没有第四次 LIVE Runner 验收。**
- Self-Runner Branch：`feature/marquez-pg14-api-web-20261013`，Workflow `.github/workflows/marquez-pg14-api-web.yml` 仍 pin **第三轮旧的 Healthcare SHA** `f815995b66461b91ec6f207efc3c49f84286f2e9`，**刻意未 Push 更新**，避免触发第四轮、破坏“三次停止”规则。
- 必须在下个明确获批的开发轮先检查修复后的 Bash `bash -n`、Helm chart 可解析和 Runner exact SHA，然后再将 Runner Workflow checkout pin 更新为最新 Healthcare Feature SHA 触发新的测试。禁止因为旧 Workflow 报 SUCCESS 之类的推测跳过实际部署验证。

## 4. 当前资源与安全状态

| 对象 | 真实状态 |
|---|---|
| `dw-postgre14` Namespace、PG14 StatefulSet/Pod/Service | 交接已存在，三轮 preflight PASS；本轮未删除/更改 |
| `dw-postgre14/dw-postgre14-data` 50Gi Retain PVC | 存在且 Bound；没有改变 |
| `dw-marquez` Namespace | 第二轮已创建 |
| `dw-marquez/marquez-db` Secret | 第二轮从 `dw-postgre14/postgres-secret` 安全复制创建；未提交明文 |
| `marquez` Helm Release、API Deployment、Web Deployment | **NOT DEPLOYED** |
| PostgreSQL14 Marquez metadata schema | **NOT MIGRATED** |
| `marquez-web-lan` NodePort 30999 | **NOT CREATED** |
| 真实 OpenLineage / Airflow / Spark | **NOT CONFIGURED** |

Secrets 只存在于 Kubernetes。保留当前 Namespace 与 Secret 可以支持下一轮幂等恢复，**无需重建 PostgreSQL14**。不要为了“清理失败”删除 PV/PVC、PG14 Pod、Secret 或原业务 DB。

## 5. 下轮唯一 NEXT（另一个明确获批的执行轮）

1. GitHub 当前 Main 对齐、对 `kubernetes/marquez/deploy-pg14.sh` 做静态 Shell/Helm Chart 校验，确认当前修复源码完整、没有 JS 字符串替换导致 Bash 的 `$'` 异常；必要时先只读 Runner 验证，禁止循环超过 3 次。
2. 更新 Self-Runner workflow 的 **exact Healthcare Feature SHA**，再以独立运行检验 Chart 固定 commit archive 下载、`helm dependency build` 和 `helm template`，确认真的只含两个 ClusterIP Service、不包含 PostgreSQL StatefulSet。
3. 只有通过上述安全门槛才运行 `helm upgrade --install`；确认 API/Web Pod Ready、DB `flyway_schema_history` 与真实 schema、持久化 readback，然后单独创建 30999 Web-only Service。
4. 事件接入另轮测试：必须标记为 `TEST`，不允许把协议探针事件冒充 TASK004 的真实 Synthea/OMOP 血缘。
5. 只有执行阶段对应 GitHub SHA 的全部 Live PASS 才 merge feature PR、将准确状态更新 `docs/demo-plan/README.md`；不改变 `dw-postgre`、TASK004、TASK005。

**交接判断：本轮已经尽力推进 Marquez 部署，真实状态是“PG14 已准备好 + Marquez Namespace/Secret 已创建，API/Web/30999 尚未部署”。三轮失败安全停止，等待下一明确执行轮继续。**
