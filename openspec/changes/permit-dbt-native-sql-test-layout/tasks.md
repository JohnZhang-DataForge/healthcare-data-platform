# Tasks — Permit Fabric dbt native SQL tests (guarded)

## P1 — Governance and offline implementation
- [x] 1.1 Confirm current Main, Ruleset-facing trusted Gate, existing tests/legacy baseline and exact dbt project owner; reject broad test exceptions.
- [x] 1.2 Design exact allowlist for `azure-fabric/dbt/hl7-canonical/tests/` with negative cases and a separate governance Change.
- [x] 1.3 Implement narrowly scoped protected checker patch, targeted test cases and read-only candidate PR-head policy check on a branch.
- [x] 1.4 [PR #815](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/815) candidate unit-test and OpenSpec CI PASS; exact head `57d91a2360ecee5613544e7b76bf0f6ff7b99d8a`, merged Main `c36ed72ba140d6b2956d71ab97206baa2965bd58`. Ruleset self-protection correctly blocked normal merge before owner-admin maintenance.

## P2 — Controlled administration (requires GitHub ruleset administrative rights)
- [x] 2.1 管理员按受保护规则维护流程完成审批并合并 PR #815；可核实证据为原 `trusted-policy-mutation` 阻断、最终 merged Main 和恢复后的 Active Ruleset #25365902。**GitHub 管理员操作的起止时刻及审批者身份当前接口未独立提供；本任务不对缺失的审计元数据作猜测。**
- [x] 2.2 PR #815 merged at `2026-11-08T02:49:16Z`, merge `c36ed72ba140d6b2956d71ab97206baa2965bd58`; independently read back protected checker code from Main, Ruleset #25365902 `enforcement=active` and original four Required contexts: `require-trusted-change`, `validate-openspec`, `require-trusted-fabric-deployment-owner`, `require-trusted-component-paths`.
- [x] 2.3 **真实 PR 正反验证**：正向 [#816](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/816) `azure-fabric/dbt/hl7-canonical/tests/.gitkeep` — 四项 Required 全部 SUCCESS，OpenSpec 和文档链接 PASS，未合并已关闭；负向 [#817](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/817) `tests/test_helper.py` — `require-trusted-change` FAIL，可信日志原文 `RULE=new-test-outside-quality EXPECTED_OWNER=.github/quality/tests/`，GitHub `mergeable_state=blocked`，未合并已关闭。正向外部 Cloudflare Workers Build 状态 FAIL，与四项 Required 无关，不作为业务部署证明。

## P3 — Independent business source

**治理验收结论（2026-11-07 ET）：** P1/P2 已实现且经主线保护正反 PR 验证。**实际 dbt 工程尚未创建**，P3 留给独立业务 PR。真实管理员 Ruleset 调整审计时间线未从当前只读接口获得，不把推定时间当成已证明事实。

- [ ] 3.1 Only AFTER P2, allow the actual `azure-fabric/dbt/hl7-canonical/` standard scaffold and SQL candidate; it belongs to a separate business PR. No Legacy HL7 cleanup in this governance Change.
