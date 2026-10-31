# Design — Fabric API Client（受控正式组件）

## Context and decisions

Self-Runner/main 现有 OIDC 信任及 `dw-runner-set` 已通过 `Fabric Healthcare Native Lineage GET-Only Probe`（Run 40251306511）访问真实 `healthcare-omop`，Fabric Item 级 GET 成功；一次旧 Trial Spark Run 40440244737 能创建/触发 Notebook 但 exitValue 读取失败。既有 P0–P2 仅离线测试。

设计限定：**一个受信任的工作流是唯一云身份入口**。任意 HTTP method/URL/Host/Headers 不能由 API 调用方直接控制；绝不把外部输入插入 Shell。第一阶段仅 Fabric 元数据读；Blob/OneLake 是不同 audience 的后续独立适配器，不谎称 Fabric Bearer 兼容。

## Data flow

```text
workflow_dispatch (validated JSON)
    -> Self-Runner/main, dw-runner-set, permissions contents:read/id-token:write
    -> src/ci/fabric_api_client.py --request-json / input ENV
    -> schema/allowlist/UUID/name validation (before token issuance)
    -> GitHub OIDC assertion (audience api://AzureADTokenExchange)
    -> Microsoft Entra token (scope https://api.fabric.microsoft.com/.default)
    -> ONLY https://api.fabric.microsoft.com/v1/<approved route>
    -> JSON status, sanitized fields, GitHub Summary and Artifact; failure -> nonzero exit
```

## API operations v1 (all GET)

1. `list_workspaces`: GET `/v1/workspaces`, filter exact `healthcare-omop` and require one match; no free enumeration in published report.
2. `list_items`: discover Workspace UUID from step 1 then GET `/v1/workspaces/{id}/items`; optional `item_type` restricted to Notebook/DataPipeline/Environment/Lakehouse/SQLEndpoint; bounded pagination.
3. `get_item`: require `item_id` canonical UUID and GET `/v1/workspaces/{id}/items/{id}`.
4. `get_job`: require `item_id` and `job_instance_id` canonical UUID, GET `/v1/workspaces/{id}/items/{id}/jobs/instances/{id}`. HTTP 200 / state `Completed` is not business acceptance; only status inspection.
5. `get_operation`: require `operation_id` canonical UUID, GET `/v1/operations/{id}`. Response bounded and sanitized.

All operations validate input BEFORE token retrieval. Do not accept arbitrary path, URL, host, HTTP method, query, headers or authorization. A bounded 429/503 retry is allowed only for GET, with `Retry-After` capped; LRO polling for read operations remains a later bounded extension. Never follow HTTP redirects to arbitrary hosts. Paging has page limit and continuation-token length cap. No payloads, definition parts or raw personal data in reports; allow only explicitly selected metadata fields.

## Request / report contract

Input is JSON as `workflow_dispatch` string (max 4 KiB), `{"schema_version":"1","request_id":"...","operation":"list_items","workspace":"healthcare-omop","item_type":"Notebook"}`. Unknown fields rejected; report records exact Self-Runner SHA, Run ID, operation, request_id, HTTP status, bounded sanitized result, error code. API exceptions fail closed. No tokens or HTTP Authorization in logs/artifacts. Manual/API dispatch is the initial supported entrypoint; existing GitHub connector does not expose a dispatch action, so it cannot independently trigger this without a separate reviewed request bridge.

## Security and testing

- Only Self-Runner/main is trusted to request GitHub OIDC. No PR-triggered self-hosted execution; static unittest CI on GitHub-hosted runner without id-token.
- Privilege is still the **existing** Fabric Service Principal; code restriction is not Entra RBAC reduction. Review branch write access/Workflow dispatch rights.
- Unit tests inject a fake transport/token provider to cover success, duplicate workspace, auth/403, 429, wrong GUID, forbidden operations and URLs, malformed JSON, data sanitization, pagination limits, and response oversize.
- Real read-only acceptance requires successful workflow_dispatch with exact run ID, SHA and `healthcare-omop` Workspace output. Test cannot prove Native Notebook/Environment or Silver data is deployed.
- Rollback is reverting the new Self-Runner workflow and client; no cloud changes to undo.

## Later stages — explicitly NOT implemented v1

- `getDefinition` is named read but actually POST in Fabric REST: independent reviewed allowlist and GET-definition LRO response handling required.
- Notebook/Pipeline run, Environment publish, Blob/OneLake independent readback require separate explicit authorization, cost/capacity checks and bounded resource-specific contracts. No generic POST/DELETE surface.
