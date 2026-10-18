# Tasks

## 1. Plan / Design

- [x] 1.1 审计 Main 的 OpenSpec CLI 工作流、G4 开发规则和 PR #225 的真实门禁失败；记录 branch protection 权限缺口。
- [x] 1.2 建立本 Change 的 Proposal、Design、Delta Spec 和 Tasks，先于本轮实现提交；不触碰业务 Runtime。

## 2. Implement / Test

- [x] 2.1 实现 `.github/quality/scripts/check_openspec_change_gate.py`，区分受保护开发路径与显式 docs-only 豁免。
- [x] 2.2 新增全面正负向单元测试；验证 PR Body/Change/Task 同步及有效 Archive。
- [x] 2.3 建立无 paths 过滤的 GitHub-hosted Change Gate 工作流；不接受无关联的实质性 PR。
- [x] 2.4 更新 `AGENTS.md`、开发工作流、OpenSpec 生命周期和状态说明；阐明 CI/归档/人工审批界限。
- [x] 2.5 完成首次 [PR #230](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/230) 新旧 CI 和 Merge；最终 PR HEAD `73a4c7dcc73b9cf0bfae2c22f0fe061fa1933b4e` 四项 CI SUCCESS（[Gate #39170772502](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39170772502)、[OpenSpec #39170772516](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39170772516)、[Component #39170772517](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39170772517)、[Docs #39170772578](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39170772578)）；Main Merge SHA `825c7ae19b091d0d407e1b28c61e55a0249e08fe`。历史首个候选 HEAD `162906577daf2ddd5d0498ab3da0cc5e087bdb9c` 上 [Change Gate #39170631410](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39170631410)、[OpenSpec #39170631407](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39170631407)、[Component #39170631435](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39170631435)、[Docs #39170631502](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39170631502) 均 SUCCESS，25 门禁测试、总计 63 质量单测、1,043 文档链接 0 失效；最终 HEAD 仍须重新校验。

- [ ] 2.6 安全加固（代码已通过 [PR #231](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/231) 合并 Main `b2064ed6445f316385f586043e15f6cf83ae0dd8`，但可信事件正/负联调尚未完成）：新增 [OpenSpec Trusted Change Gate](../../../.github/workflows/openspec-trusted-change-gate.yml)，使用 `pull_request_target` 默认分支受信任策略脚本与单测、仅把 PR Head 当只读文件/树数据，不执行候选代码；它首次合并到 Main 以后需要用独立 PR 进行真实正/负触发验证。GitHub 当前文档指出公共仓库默认事件策略于 2026-11-02 开始阻断 `pull_request_target`，管理员须检查相应 Actions Policy；不允许把暂时成功当作长期可用。

- [ ] 2.7 核验可信门禁真实 PR 的 PASS/FAIL 与 Main required check 绑定；如无法读取/修改分支规则或事件策略，清晰登记 HOLD 和人工后续动作。

## 3. Merge / Protection

> 受审 PR 对应 OpenSpec-Change: enforce-openspec-change-gate；首次 CI 成功或失败的实际 Run 由后续准确 HEAD 验证补证，不预先标记所需门禁完成。


- [ ] 3.1 核对/审查最终 PR Diff、Merge 完成，记录确切 Main SHA。
- [ ] 3.2 配置并核验 Main 对 `OpenSpec Change Gate / require-change` 的 required status；若当前 GitHub 集成没有此权限，记录明确的**未完成**用户管理步骤，不得标注 PASS。
- [ ] 3.3 完成后续治理验收、同步 Current Specs 与本 Tasks，并按 OpenSpec Archive 规则单独归档；用户未授权任何业务 E2E，绝不混淆。

## 4. Evidence / HOLD

- 原始事实：原 PR #225 Component Naming FAIL 而被合并；PR #228–#229 的追溯记录已有独立完成 SHA `a082273b0de98b201aa5adee30dd397e5d40082f`。
- Main 当前 `protected=true`，但读取 `branches/main/protection` 返回 GitHub 403 Resource not accessible by integration；Required Checks/Bypass 的状态未经确认。
- 现有 `relocate-local-data-platform` Active Change 保持独立管理，不提前归档，不允许本治理工作触发运行时读写。
