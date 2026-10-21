# Design

## Decisions

1. `fabric-workspace/healthcare-omop/workspace/` Terraform 是 Workspace 的**唯一管理者**；该 Root 提供 `capacity_id` 引用，Capacity REST 模块绝不更改它。继续采用用户指定的同级 `capacity-api/` 源码目录，但其对象是外部 Capacity、不是新的 Terraform Root，也没有 State。
2. Trial `inspect` 通过 `https://api.fabric.microsoft.com/v1/capacities/{guid}`。当前试用 F4、免费、截止期由平台管理；不提供 suspend/resume，不允许把 Trial GUID 当成正式 Azure ARM Resource ID。
3. 付费 Capacity 通过 `https://management.azure.com/{ARM-ID}?api-version=2023-11-01` GET，`POST .../suspend` 或 `POST .../resume`。目标必须是已存在且属于指定订阅的 Microsoft.Fabric/capacities ARM ID。独立付费 Terraform Root 负责规格/创建与费用审批；运行态暂停/恢复由 REST Controller 管理。付费 Capacity 可能被多个 Workspace 共用，暂停会影响全部使用者。
4. 使用 GitHub OIDC JWT 和 Entra `client_credentials` 联合身份换取不同 Audience 的令牌；禁止保存 client secret、禁止输出 JWT/Bearer token。Trial GET 仍要求应用是 Capacity Admin/Contributor，否则正常失败而非自动提权。
5. 操作默认 `inspect`。付费修改必须 `ENABLE_PAID_CAPACITY_OPERATIONS=true` 且 `CAPACITY_ACTION_CONFIRM` 与操作一致；未收到用户真实执行授权，创建 Workflow 不会自动触发修改。对 API POST 202 后必须 GET 验证最终状态，未知结果保持 FAIL/HOLD 不自动重复 POST。
6. 不设置自动定时恢复；恢复会重启计费，禁止从缓存/已废弃变量推断付费 Resource ID。OneLake Storage 费用可能在暂停时继续，超额计算可能在暂停时结算。

## Tests

- Unit Mock 测 Trial 只读、trial 修改拒绝、跨订阅 ARM-ID 拒绝、成本门禁、suspend/resume/idempotent、异步读回、无 Workspace REST API。
- Self-Runner 静态 YAML/Bash 验证允许模式/操作、无自动触发和 Azure identity/Git SHA Gate。
- Runtime GET 或真实 suspend/resume 需要独立已确认的运行授权，绑定正确容量后补充 Run 证据。

## References

- https://learn.microsoft.com/en-us/rest/api/fabric/core/capacities/get-capacity
- https://learn.microsoft.com/en-us/rest/api/microsoftfabric/fabric-capacities/suspend?view=rest-microsoftfabric-2023-11-01
- https://learn.microsoft.com/en-us/rest/api/microsoftfabric/fabric-capacities/resume?view=rest-microsoftfabric-2023-11-01
- https://learn.microsoft.com/en-us/fabric/enterprise/pause-resume
