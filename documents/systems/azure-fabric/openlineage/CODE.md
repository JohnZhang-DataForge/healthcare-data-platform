---
status: active
scope: azure-fabric-openlineage-source-map
last_verified: 2026-11-04
source_sha: 5a7bd15977b307c358ff50155888a58f813e06ed
---

# Fabric OpenLineage — CODE 源码地图

Publisher 业务实现仍位于 `azure-fabric/openlineage/`，Listener 部署配置位于 `azure-fabric/deployment/openlineage/`；不得复制至 Native Notebook 或建立第二个 Publisher。本次 P2 仅移动说明文件，保留现有业务源码、15 个 Fabric 测试及 CI 路径。

| 源码/测试 | 目的 |
| --- | --- |
| [compatibility.py](../../../../azure-fabric/deployment/openlineage/compatibility.py) | Fabric Spark 4.1/Scala 2.13 Listener 候选配置，未通过 Live Fabric 验收 |
| [publisher.py](../../../../azure-fabric/openlineage/publisher.py) | 本地注入 ContainerClient 的不可变 Blob Event Publisher |
| [test_compatibility.py](../../../../.github/quality/tests/azure-fabric/openlineage/test_compatibility.py) | 迁移后统一 CI 兼容性回归测试；仍为离线候选 |
| [test_publisher.py](../../../../.github/quality/tests/azure-fabric/openlineage/test_publisher.py) | 迁移后统一 CI 的 Fake SDK/不可变上传/恢复安全测试 |

**权威说明**：[组件职责与试验边界](README.md)、[Publisher 协议](PUBLISHER.md)。当前仅离线源码候选；真实 Azure Blob Collector/凭据/Marquez 集成仍需要独立授权与运行验收。

## P3.2 新测试所有权与发现断言

两个离线回归测试现在仅在 `.github/quality/tests/azure-fabric/openlineage/` 更新，原源代码 `azure-fabric/openlineage/{compatibility,publisher}.py` 不变。专用 [Fabric OpenLineage Offline CI](../../../../.github/workflows/fabric-openlineage-offline.yml) 必须发现 **2 个文件/至少 8 个测试用例并真正执行**。测试 PASS 不代表 Azure Blob 发布或 Fabric Listener 已上线。
