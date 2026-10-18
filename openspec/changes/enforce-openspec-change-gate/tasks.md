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

- [x] 2.6 安全加固已通过 [PR #231](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/231) 合并 Main `b2064ed6445f316385f586043e15f6cf83ae0dd8`；可信 `pull_request_target` 在 Base 中运行 Checker/单测，只把 PR Head 当静态候选。使用真实 [PR #232](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/232) 验证：[正确声明 Run #39171185260](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39171185260) **PASS**；编辑 Body 暂时移除声明，[负向 Run #39171214471](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39171214471) **预期 FAIL**（明确缺少 OpenSpec-Change 和 OpenSpec-Task）；恢复正确声明后 [Run #39171247693](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39171247693) **PASS**。每轮均 25 测试通过，PR Head `1ddb31d88e9ac0f213577db5a1b59d4f5dbb56c0`；负向故障为预期策略拒绝，不是实现调试失败。

- [ ] 2.7 可信门禁真实 PR 正/负 PASS/FAIL **已核验（详见 2.6）**；Main Required Check / Bypass 的读取与设置仍因当前集成在 `branches/main/protection` 获得 HTTP 403 而 **HOLD**。公开仓库 `pull_request_target` 的 2026-11-02 事件策略需要管理员确认可执行性；不得仅凭目前 PASS 宣称长期强制合并保护。

## 3. Merge / Protection

> 受审 PR 对应 OpenSpec-Change: enforce-openspec-change-gate；首次 CI 成功或失败的实际 Run 由后续准确 HEAD 验证补证，不预先标记所需门禁完成。


- [x] 3.1 完成实际实施 [PR #230](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/230)（Main Merge `825c7ae19b091d0d407e1b28c61e55a0249e08fe`）与可信门禁 [PR #231](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/231)（Main Merge `b2064ed6445f316385f586043e15f6cf83ae0dd8`），两者最终 PR HEAD 原有 OpenSpec/组件/链接/普通 Gate CI 均成功；#231 的可信事件因未进入 Base 尚无法在自身 PR 验证，后由 PR #232 的正反向运行证明。

- [ ] 3.2 配置并核验 Main 对 `OpenSpec Change Gate / require-change` 的 required status；若当前 GitHub 集成没有此权限，记录明确的**未完成**用户管理步骤，不得标注 PASS。
- [ ] 3.3 完成后续治理验收、同步 Current Specs 与本 Tasks，并按 OpenSpec Archive 规则单独归档；用户未授权任何业务 E2E，绝不混淆。

## 4. Evidence / HOLD

- 原始事实：原 PR #225 Component Naming FAIL 而被合并；PR #228–#229 的追溯记录已有独立完成 SHA `a082273b0de98b201aa5adee30dd397e5d40082f`。
- Main 当前 `protected=true`，但读取 `branches/main/protection` 返回 GitHub 403 Resource not accessible by integration；Required Checks/Bypass 的状态未经确认。
- 现有 `relocate-local-data-platform` Active Change 保持独立管理，不提前归档，不允许本治理工作触发运行时读写。


## 5. 外部管理员操作（待确认，绝不冒充已完成）

1. 进入 Healthcare GitHub 仓库 Settings → Branches / Rulesets（适用的 Main protection），将 **`OpenSpec Trusted Change Gate / require-trusted-change`** 设为 Required status check；核查管理员/自定义 bypass、PR review 要求及任何“跳过检查合并”能力。
2. 进入 Actions 事件/组织 Policy，确认本公共仓库所用的受信任、只读 `pull_request_target` 用法在 GitHub 2026-11-02 默认事件策略强制生效后依旧允许运行。仓库的事件策略须明确允许安全用法，不可把策略拦截当作成功。
3. 为验证 Required 真正阻止合并，可在下一轮独立创建受控负向 PR（不合并），观察 GitHub 明确显示 required check 阻断，而不仅是 CI 红灯。权限核实前 Tasks 2.7 / 3.2 / 3.3 继续未完成。
