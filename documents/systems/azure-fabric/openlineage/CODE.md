---
status: active
scope: azure-fabric-openlineage-source-map
last_verified: 2026-11-04
source_sha: 5a7bd15977b307c358ff50155888a58f813e06ed
---

# Fabric OpenLineage — CODE 源码地图

唯一实现位于 `azure-fabric/openlineage/`；不得复制至 Fabric Git Notebook 或建立新的 Publisher 业务模块。本次 P2 仅移动说明文件，保留现有业务源码、15 个 Fabric 测试及 CI 路径。

| 源码/测试 | 目的 |
| --- | --- |
| [compatibility.py](../../../../azure-fabric/openlineage/compatibility.py) | Fabric Spark 4.1/Scala 2.13 Listener 候选配置，未通过 Live Fabric 验收 |
| [publisher.py](../../../../azure-fabric/openlineage/publisher.py) | 本地注入 ContainerClient 的不可变 Blob Event Publisher |
| [test_compatibility.py](../../../../azure-fabric/openlineage/tests/test_compatibility.py) | 旧路径冻结兼容性测试；P3 单独迁移 |
| [test_publisher.py](../../../../azure-fabric/openlineage/tests/test_publisher.py) | 旧路径冻结的 Fake SDK、不可变上传及恢复测试；P3 单独迁移 |

**权威说明**：[组件职责与试验边界](README.md)、[Publisher 协议](PUBLISHER.md)。当前仅离线源码候选；真实 Azure Blob Collector/凭据/Marquez 集成仍需要独立授权与运行验收。
