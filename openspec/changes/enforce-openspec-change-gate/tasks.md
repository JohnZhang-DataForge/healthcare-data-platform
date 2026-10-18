# Tasks

## 1. Plan / Design

- [x] 1.1 审计 Main 的 OpenSpec CLI 工作流、G4 开发规则和 PR #225 的真实门禁失败；记录 branch protection 权限缺口。
- [x] 1.2 建立本 Change 的 Proposal、Design、Delta Spec 和 Tasks，先于本轮实现提交；不触碰业务 Runtime。

## 2. Implement / Test

- [x] 2.1 实现 `.github/quality/scripts/check_openspec_change_gate.py`，区分受保护开发路径与显式 docs-only 豁免。
- [x] 2.2 新增全面正负向单元测试；验证 PR Body/Change/Task 同步及有效 Archive。
- [x] 2.3 建立无 paths 过滤的 GitHub-hosted Change Gate 工作流；不接受无关联的实质性 PR。
- [x] 2.4 更新 `AGENTS.md`、开发工作流、OpenSpec 生命周期和状态说明；阐明 CI/归档/人工审批界限。
- [ ] 2.5 完成首次 PR #230 的新旧 CI 精确 HEAD 校验与 Merge，记录 SHA/Run；当前首个候选 HEAD `162906577daf2ddd5d0498ab3da0cc5e087bdb9c` 上 [Change Gate #39170631410](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39170631410)、[OpenSpec #39170631407](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39170631407)、[Component #39170631435](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39170631435)、[Docs #39170631502](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39170631502) 均 SUCCESS，25 门禁测试、总计 63 质量单测、1,043 文档链接 0 失效；最终 HEAD 仍须重新校验。

- [ ] 2.6 安全加固：待 #230 合并使检查器进入 Main 后，另一个 PR 从受信任 Main/Base checkout 执行 Checker，只将 PR Head 当作静态待检查数据；防止 PR 直接修改自身验证器使同轮 PASS，验证新 PR HEAD 与对应 Runs。

## 3. Merge / Protection

> 受审 PR 对应 OpenSpec-Change: enforce-openspec-change-gate；首次 CI 成功或失败的实际 Run 由后续准确 HEAD 验证补证，不预先标记所需门禁完成。


- [ ] 3.1 核对/审查最终 PR Diff、Merge 完成，记录确切 Main SHA。
- [ ] 3.2 配置并核验 Main 对 `OpenSpec Change Gate / require-change` 的 required status；若当前 GitHub 集成没有此权限，记录明确的**未完成**用户管理步骤，不得标注 PASS。
- [ ] 3.3 完成后续治理验收、同步 Current Specs 与本 Tasks，并按 OpenSpec Archive 规则单独归档；用户未授权任何业务 E2E，绝不混淆。

## 4. Evidence / HOLD

- 原始事实：原 PR #225 Component Naming FAIL 而被合并；PR #228–#229 的追溯记录已有独立完成 SHA `a082273b0de98b201aa5adee30dd397e5d40082f`。
- Main 当前 `protected=true`，但读取 `branches/main/protection` 返回 GitHub 403 Resource not accessible by integration；Required Checks/Bypass 的状态未经确认。
- 现有 `relocate-local-data-platform` Active Change 保持独立管理，不提前归档，不允许本治理工作触发运行时读写。
