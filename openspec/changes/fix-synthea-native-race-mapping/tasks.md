# Tasks

> 状态：仅方案和诊断证据确认，**业务修复未实施**。此 Change 唯一管理 `native` Race Mapping 的业务修复；原 [`relocate-local-data-platform`](../relocate-local-data-platform/tasks.md) 继续管理镜像 E2E、历史 Shell/测试与 GHCR 退役。本文不授予任何 PG/K8s/GHCR 写操作许可。

## 1. 冻结证据与方案

- [x] 1.1 核对早晨成功 Batch [旧/新 Writer A/B #39534932448](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39534932448)、失败 Batch [A/B #39535834807](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39535834807) 的输入行数、固定 Digest、实际 Pod 和 `native` 唯一未映射值；保留其它随机失败 Batch 的不确定性。
- [x] 1.2 建立本 Proposal、Design、Tasks、可测试 Delta Spec，并同步原迁移 Change 的 4.11.5/4.11.6/清理次序；方案 PR 不变更业务数据与镜像。
- [ ] 1.3 在方案 PR 最终 HEAD 上验证 OpenSpec Strict、Change Gate、Trusted Gate、文档链接和适用 CI 后合并；文档合并不等于缺陷修复。

## 2. 修复映射与回归

- [ ] 2.1 核对 Synthea v3.3.0 `native` 的源值语义、当前 OMOP CDM 5.4 所用词表中的有效标准 Concept ID，并附可复核依据；未确认时停止，不猜测、不使用 `0` 兜底。
- [ ] 2.2 最小化修复 `task004_cdm_dynamic_adapters.py` 的 Race Mapping，并评估预提交映射检查与错误信息；不改变已有 Source Key、Fingerprint、Visit Parent、Writer Fence/SQL、DAG。
- [ ] 2.3 增加 `native` 与已支持值的正向回归、非法值负向回归及映射确定性/行数/不落库验证，所有 Unit/Contract 通过。
- [ ] 2.4 在绑定最新 Main 的源码 PR 上运行适用 CI/构建/静态门禁，保留来源 SHA 和原始证据，核对组件 CODE.md 后合并。

## 3. 真实只读回归与跨 Change E2E

- [ ] 3.1 用原失败 Batch `synthea-new-only-gh-39524542198` 不可变 Parquet 做修复后**只读** Person/Visit 映射验证，确保 64/12,446 行且 `native` 映射语义正确，**不清 PG、不 COMMIT、不复写历史 Ledger**。
- [ ] 3.2 将已合并修复移交迁移 Change Task **4.11.5**：重新构建/发布受影响镜像并使用**新生成** Batch 完整 E2E、PG/S3 独立读回与同 Batch SKIP；结果只由原 4.11.5 记录，未通过时保持 HOLD。
- [ ] 3.3 依据代码/回归和迁移 E2E 的真实状态决定何时归档，不提前将计划写成已采用 Current Spec。
