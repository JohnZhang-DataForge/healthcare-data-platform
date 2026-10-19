# Local DP 4.2 — 首轮 Repository Root 静态测试修复

> 2026-10-19 · PARTIAL / HOLD，OpenSpec Change: `relocate-local-data-platform`；基线 Main `882a7248f059508b2c135403b3bf3ad01438f604`。仅调整静态测试路径，不执行脚本、镜像构建、GHCR 发布或任何业务 Runtime。

## 已修复路径

- `local-data-platform/tests/task004/test_synthea_ghcr_workflow.py`：`WORKFLOW` 从错误的 Platform Root 下 `.github/workflows` 改为真实 Repository Root 下 `.github/workflows`，`DOCKERFILE` 仍由 Platform Root 解析。
- `local-data-platform/tests/task004/test_unified_runtime_image_source.py`：同样修复 `WORKFLOW`；Dockerfile、Entrypoint、Kubernetes Manifest、Task004 Shell 仍以 Platform Root 定位。
- 该修复不是移除旧测试断言，也未改变 Writer/DAG/镜像业务行为。

## 确认仍阻塞的兼容问题

1. `.github/workflows/build-synthea-image.yml`：`context: .` 与 `file: ./images/synthea/Dockerfile` 仍采用迁移前的根布局；路径过滤也保留 `images/synthea/**`、`apps/task004/**` 和 `contracts/**`。
2. `.github/workflows/build-task004-runtime-image.yml`：构建前脚本、镜像路径、`cmp`、测试发现路径和 `context: .` 均指向旧根路径；其生成器 `scripts/task004/06a-prepare-unified-runtime-image.sh` 仍可能覆写源码，严禁为验证而运行。
3. 两份现存单测还保留部分旧路径字面断言，故此次仅修复对象定位，不声称其完整测试套件 PASS。
4. Clean Build、模块实际来源 `__file__`、镜像 Digest、DAG Parse 和 Live GitSync 尚无新验证。4.2、4.3、4.4 均 OPEN；4.9 删除仍 HOLD。

## 下一步

以组件依赖为界分别审计并修复 Workflow Build Context、Docker COPY、脚本/生成器、Trigger Paths、测试字面断言；使用不发布镜像的隔离源码检查，再经授权的实际 Clean Build / DAG 门禁。三个历史文档生成器仍保存并可经固定 SHA 恢复，不能在此次 PR 删除。
