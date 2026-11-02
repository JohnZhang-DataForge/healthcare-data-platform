# Tasks

- [x] 1.1 对照当前两仓 main、已验证 P3 Git 运行链及 Microsoft Git Status/UpdateFromGit 文档，明确固定 Allowlist 无法创建新 Notebook 的根因。
- [x] 1.2 建立本 Change，冻结 Git 主权威、原业务 HALT、独立云端创建验收、失败关闭边界。
- [x] 2.1 Healthcare Dispatch Workflow 接受新的 Git-native Notebook 文件变更；相应自动化路径测试及 Notebook CODE/Runbook 更新。
- [x] 2.2 Self-Runner 添加 root-level Git Native Notebook 新建的精确身份验证、remote Added、Source/HALT/Environment Gate、混杂状态 HOLD，保留现有固定项逻辑。
- [x] 2.3 Self-Runner 增加 UpdateFromGit 后的独立新 Notebook identity/content/env readback，以及负向单测；PR CI PASS。
- [x] 3.1 Healthcare PR 与 Self-Runner PR 均完成 Required CI、合并 main；记录准确 SHA、Run 和本次授权范围。
- [ ] 3.2 使用新无业务数据的 Git-native Notebook 进行真实 Added → UpdateFromGit → Readback 验收（需要独立 reviewed 验证和审慎清理）。在此之前 `LIVE_NEW_NOTEBOOK_UNVERIFIED`。
- [ ] 3.3 正式业务 `nb_fhir_ingest` 的受控运行时 Smoke 单独后续处理，保持 HALT；本 Change 不声明业务 ETL PASS。

## Evidence

- Self-Runner PR #420 merged as `094714f86b7ca7abb62e49cab319423a91eeba2c`; CI Run 41468951822 passed.
- Healthcare PR #602 source gate is passing; new Notebook Added cloud E2E remains NOT_RUN.

## Final merged evidence — 2026-11-02

- **Private Self-Runner** [PR #420](https://github.com/JohnZhang-DataForge/Self-Runner/pull/420), reviewed HEAD `f8872ad0de5194543d4ec9f1711737ded966d709`, merged main `094714f86b7ca7abb62e49cab319423a91eeba2c`; offline [Run 41468951822](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41468951822) PASS. Post-merge main [Run 41469096085](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41469096085) has both jobs SUCCESS, updater reported `HOLD_REMOTE_SHA_WITHOUT_ITEMS`, `WRITE_ATTEMPTED=False`, `ERROR=NONE`.
- **Healthcare** [PR #602](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/602), reviewed HEAD `2d6e1cc4f00691262b949dcc7a837be1daa31059`, merged main `1216f53eeca3105367438460734b14555a3bb325`. Final PR HEAD checks PASS: [Fabric Git Deploy 41469209710](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41469209710), Component Code Naming 41469209777, OpenSpec Change Gate 41469209771, Static Validation 41469209736, Documentation Links 41469209737, trusted change Required Gate PASS. Unrelated Cloudflare Workers Build failed but was not a required blocker.
- **Live main push dispatch chain:** Healthcare [Run 41469405905](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41469405905) validated and dispatched exact main SHA; private Self-Runner [Run 41469448834](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41469448834) both jobs SUCCESS with `HOLD_REMOTE_SHA_WITHOUT_ITEMS`, `WRITE_ATTEMPTED=False`, `ERROR=NONE`. This is correct for a commit changing only Workflow/OpenSpec/documents, not Fabric Native Item definitions; it proves dispatch and no spurious write, **not** remote `Added` actual creation.
- **Unverified boundary:** Task 3.2 remains `LIVE_NEW_NOTEBOOK_UNVERIFIED` pending a newly approved, isolated Git-native Notebook definition and independent Fabric physical Item/GetDefinition readback. Task 3.3 business Notebook Runtime/ETL remains separate, and HALT is retained. No Notebook/Pipeline executed, no Environment published, no Delta business data written in these runs.

## Live test plan — 2026-11-02 (authorized, not yet executed)

- Temporary Git-native item: `nb_git_onboarding_smoke.Notebook`, new source logicalId `9d256d25-6f0a-4d73-9ca2-2206f874a501`, only two native files `.platform` and `notebook-content.py`.
- Only permitted Spark code: import `healthcare_data_engine`, require Wheel 0.1.1 and PySpark 4.1, return `FABRIC_GIT_NEW_NB_ENGINE_011_SPARK41_PASS_20261102`; **no** business/Delta/Blob/Lakehouse I/O.
- Sequence: Healthcare PR offline CI → main merge → main push Dispatch → Self-Runner Git Status `remoteChange=Added` → single `UpdateFromGit` → independently confirm physical Notebook identity, .py/ipynb code & Environment → separately reviewed smoke job with exact exit value → Git-native teardown and cloud delete → independent Item/Git Status verification.
- **Not completed** until all three stages succeed: `LIVE_GIT_NOTEBOOK_CREATED`, `LIVE_GIT_NOTEBOOK_JOB_EXIT_PASS`, `LIVE_GIT_NOTEBOOK_DELETED_AND_GIT_CLEAN`. When failures occur, keep exact id/run/unknown ACK and never delete any business Notebook.

## Real create and Spark execution PASS; Git-native teardown pending (2026-11-02)

- **Real Git Added**: Healthcare PR #604 merged main `624b9e7664205447d77ce5f845564d2995f4ea23`. Self-Runner [Run 41476737114](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41476737114) caught a new Native Git Status response where `remoteChange=Added` and logicalId were valid but `fileChanges` omitted even with `includeFilesDetails=true`. Safe HOLD; no cloud mutation. Self-Runner [PR #422](https://github.com/JohnZhang-DataForge/Self-Runner/pull/422) fixed ONLY this case.
- **Git-created item really deployed**: Self-Runner [Run 41478131139](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41478131139) `AUTO_UPDATE_DEPLOYMENT_READBACK_PASS`, `new_notebook_definitions_equal_git=true`, unchanged business Notebook cells and Pipeline HALT parameters. Physical ID `32fee30f-6787-4a04-a8c7-ca7c579dbd69`, logicalId `9d256d25-6f0a-4d73-9ca2-2206f874a501`.
- **Actual Spark execution PASS**: Self-Runner [Run 41478807776](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41478807776) executed the **same Git-created Notebook**. Job `d7f4e84b-2752-4356-be04-914862edadb3` `Completed`, exact `exitValue=FABRIC_GIT_NEW_NB_ENGINE_011_SPARK41_PASS_20261102`; Spark 4.1 + Wheel 0.1.1 import; `business_data_reads=false`, `delta_writes=false`.
- **Observed drift after execution**: existing general auto-updater reports `UNAPPROVED_LOCAL_ITEM_PRESENT` for the disposable Notebook. This is not a failed Spark Job; clean up via exact-item `remoteChange=Deleted`, independently readback pinned business item identities, and restore Git status. Until cleanup is truly PASS, task 3.2 remains unchecked. [Self-Runner cleanup PR #424](https://github.com/JohnZhang-DataForge/Self-Runner/pull/424) implements this guarded one-time path.
