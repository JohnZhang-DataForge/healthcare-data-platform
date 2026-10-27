# On-demand Healthcare Demo Trigger and Read-only Status

## ADDED Requirements

### Requirement: Anonymous GET never initiates billable computation

系统 SHALL 向所有匿名访客提供最近一次成功运行的脱敏静态快照，并且任何 GET、预览、爬虫访问或刷新都 MUST NOT 调用 GitHub Workflow、Notebook、Azure Capacity Resume 或业务 Generator。自动触发仅能来自符合条件的真实用户会话，通过服务器端 Turnstile 核验后的受控 POST，且必须在所有开关/配额门槛通过时执行。

#### Scenario: Link preview visits public website

- **GIVEN** 一个搜索引擎爬虫或邮件链接预览访问公开页面
- **WHEN** 客户端发送 GET 请求而没有通过真人校验及触发 POST
- **THEN** 页面 SHALL 返回上次成功的只读快照，并 MUST NOT 触发业务任务、成本计算或计入已接受次数

### Requirement: Strict geographic, per-IP, global and concurrency budgets

受理控制器 SHALL 只允许可信 Cloudflare 服务器端判断为 US 的请求，以服务端密钥形成的短期 HMAC IP 配额标识为单位每 UTC 日最多受理 3 次，同时实施可配置的全站每日上限、月度成本/时长熔断、全局一个 Active E2E 和原子去重预留。初始全站 6 次/日是待实测可收紧的安全默认值，不是允许绕过财务审批的依据。

#### Scenario: Fourth US request in UTC day

- **GIVEN** 同一个 IP 的三个请求已经在当前 UTC 日受理
- **WHEN** 第四个请求通过了 Turnstile 检查
- **THEN** 系统 MUST 拒绝新的 Dispatch，并 SHALL 继续提供历史静态快照

#### Scenario: Concurrent requests from different US IPs

- **GIVEN** 一个 Active E2E 已经占用唯一运行槽
- **WHEN** 两个合格访客几乎同时请求触发
- **THEN** 原子门槛 MUST 防止创建第二个并发 E2E 或超卖全站额度

#### Scenario: Non-US IP or spoofed location header

- **GIVEN** 访问者不是 Cloudflare 验证的 US 来源，或客户端试图伪造国家请求 Header
- **WHEN** 请求发往触发控制器
- **THEN** 不可信输入 MUST NOT 替代 Worker 服务端地域判断，也不得启动业务任务

### Requirement: Administrator gate and paid capacity are independent

系统 MUST 提供受保护的管理员配置入口控制 OFF、ON 和 Emergency OFF，默认 OFF；网站不得访问 GitHub Token/ARM Secret 或选择任意 Workflow/Shell。开启自动访客触发 MUST NOT 自动购买、恢复或启动付费 F SKU。未单独批准费用时只能使用已授权的免费资源与受限演示方式。

#### Scenario: Auto trigger enabled while paid capacity not approved

- **GIVEN** 管理员已把访客自动触发打开，但 paid SKU 运行未获独立授权
- **WHEN** 自动调度尝试执行 Fabric paid Backend
- **THEN** 系统 MUST fail closed 且 MUST NOT 自动恢复收费容量

### Requirement: Honest status, email and failure recovery

状态界面 SHALL 显示仅来自 Runner/Blob/Spark/Marquez 真实读回的进度；原始 Job 成功但血缘同步失败时 MUST NOT 标记整个 E2E COMPLETE。邮件发送仅针对指定管理员邮箱，按 request_id 去重；事故后历史成功展示仍然可见。

#### Scenario: Fabric succeeds but lineage relay is offline

- **GIVEN** Spark 数据结果已经验证，而本地 Marquez 无法连接
- **WHEN** 浏览器查看新批次状态
- **THEN** 状态 SHALL 显示等待血缘同步或失败，并继续提供之前成功快照，不得谎报已完成端到端链路
