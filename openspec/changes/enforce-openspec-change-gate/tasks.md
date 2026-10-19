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

- [x] 2.7 可信门禁真实 PR 正/负 PASS/FAIL 已核实（见 2.6）；新 Main Required Ruleset 下负向 PR #233 的可信 [Run #39184336443](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39184336443) 预期 FAIL 且 GitHub `mergeable_state=blocked`，PR 已关闭未合并。运行时与未来事件策略另行监控。

## 3. Merge / Protection

> 受审 PR 对应 OpenSpec-Change: enforce-openspec-change-gate；首次 CI 成功或失败的实际 Run 由后续准确 HEAD 验证补证，不预先标记所需门禁完成。


- [x] 3.1 完成实际实施 [PR #230](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/230)（Main Merge `825c7ae19b091d0d407e1b28c61e55a0249e08fe`）与可信门禁 [PR #231](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/231)（Main Merge `b2064ed6445f316385f586043e15f6cf83ae0dd8`），两者最终 PR HEAD 原有 OpenSpec/组件/链接/普通 Gate CI 均成功；#231 的可信事件因未进入 Base 尚无法在自身 PR 验证，后由 PR #232 的正反向运行证明。

- [x] 3.2 已核验正式 [Main Ruleset #25365902](https://github.com/JohnZhang-DataForge/healthcare-data-platform/rules/25365902)：`active`、默认分支、Required GitHub Actions `require-trusted-change` + `validate-openspec`、审批 0、Squash、禁止删除/Force Push；`bypass_actors=[]`、`current_user_can_bypass=never`。实际 PR #233 缺少关联时 blocked。未来事件策略及其他权限主体仍需持续核查。
- [ ] 3.3 完成后续治理验收、同步 Current Specs 与本 Tasks，并按 OpenSpec Archive 规则单独归档；用户未授权任何业务 E2E，绝不混淆。

## 4. Evidence / HOLD

- 原始事实：原 PR #225 Component Naming FAIL 而被合并；PR #228–#229 的追溯记录已有独立完成 SHA `a082273b0de98b201aa5adee30dd397e5d40082f`。
- Main 当前 `protected=true`，但读取 `branches/main/protection` 返回 GitHub 403 Resource not accessible by integration；Required Checks/Bypass 的状态未经确认。
- 现有 `relocate-local-data-platform` Active Change 保持独立管理，不提前归档，不允许本治理工作触发运行时读写。


## 5. 已配置的管理规则与未来复核

1. **已完成（2026-10-18）**：Main Ruleset #25365902 要求 `require-trusted-change` 和 `validate-openspec`；审批数 0，Bypass 空，当前用户不可绕过。旧 Branch Protection 的独立细节接口 403，不据此声称已完整审计其他潜在遗留规则。
2. 进入 Actions 事件/组织 Policy，确认本公共仓库所用的受信任、只读 `pull_request_target` 用法在 GitHub 2026-11-02 默认事件策略强制生效后依旧允许运行。仓库的事件策略须明确允许安全用法，不可把策略拦截当作成功。
3. **已完成负向验证**：受控 PR #233 的 `require-trusted-change` FAIL，而 `validate-openspec` PASS，GitHub 返回 `mergeable_state=blocked`；PR 已关闭且未合并。正向 PR 合并证据仍需核对，Task 3.3 依旧未完成。


## 6. Main Required Gate 真实验证（2026-10-18 EDT）

- [Main Ruleset #25365902](https://github.com/JohnZhang-DataForge/healthcare-data-platform/rules/25365902) 已在 Main 生效：`active`，`~DEFAULT_BRANCH`，Required Jobs `require-trusted-change` + `validate-openspec`，Source GitHub Actions，0 人工审批，Squash-only，禁止删除/Force Push，`bypass_actors=[]`，`current_user_can_bypass=never`。
- [负向 PR #233](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/233)：故意不填 Change/Task 的受控文档文件，仅在未合并测试分支；可信 [Run #39184336443](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39184336443) `OPENSPEC_CHANGE_GATE=FAIL`，理由 `Require OpenSpec-Change and OpenSpec-Task on separate PR body lines`；`validate-openspec` PASS，GitHub `mergeable_state=blocked`。PR 已关闭且未合并，没有尝试对违规 PR 调用 Merge API。
- 正向规则测试：本 PR 提供正确 `OpenSpec-Change`、`OpenSpec-Task` 与同 PR 的 `tasks.md` 更新，之后据实记录 Required CI、GitHub Merge state 和是否能无人工审批完成合并；上述负向事实与正向尚未执行的事项明确区分。
- Required Gate 与本轮验证只证明已覆盖的自动检查与权限状态；不保证设计本身正确，也不代表业务运行 E2E。未来 GitHub Actions 事件策略变化仍需额外核查。
