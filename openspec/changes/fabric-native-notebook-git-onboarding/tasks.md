# Tasks

- [x] 1.1 对照当前两仓 main、已验证 P3 Git 运行链及 Microsoft Git Status/UpdateFromGit 文档，明确固定 Allowlist 无法创建新 Notebook 的根因。
- [x] 1.2 建立本 Change，冻结 Git 主权威、原业务 HALT、独立云端创建验收、失败关闭边界。
- [x] 2.1 Healthcare Dispatch Workflow 接受新的 Git-native Notebook 文件变更；相应自动化路径测试及 Notebook CODE/Runbook 更新。
- [x] 2.2 Self-Runner 添加 root-level Git Native Notebook 新建的精确身份验证、remote Added、Source/HALT/Environment Gate、混杂状态 HOLD，保留现有固定项逻辑。
- [x] 2.3 Self-Runner 增加 UpdateFromGit 后的独立新 Notebook identity/content/env readback，以及负向单测；PR CI PASS。
- [ ] 3.1 Healthcare PR 与 Self-Runner PR 均完成 Required CI、合并 main；记录准确 SHA、Run 和本次授权范围。
- [ ] 3.2 使用新无业务数据的 Git-native Notebook 进行真实 Added → UpdateFromGit → Readback 验收（需要独立 reviewed 验证和审慎清理）。在此之前 `LIVE_NEW_NOTEBOOK_UNVERIFIED`。
- [ ] 3.3 正式业务 `nb_fhir_ingest` 的受控运行时 Smoke 单独后续处理，保持 HALT；本 Change 不声明业务 ETL PASS。

## Evidence

- Self-Runner PR #420 merged as `094714f86b7ca7abb62e49cab319423a91eeba2c`; CI Run 41468951822 passed.
- Healthcare PR #602 source gate is passing; new Notebook Added cloud E2E remains NOT_RUN.
