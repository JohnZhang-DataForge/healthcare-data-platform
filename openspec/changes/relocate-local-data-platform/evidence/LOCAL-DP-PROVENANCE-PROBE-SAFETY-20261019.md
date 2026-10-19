# Local DP 只读来源探针安全补强（2026-10-19）

基线 Main：`bf8cddcc470c42e43d495af1571bde377b1514c1`；Change `relocate-local-data-platform`，Task 4.4。

对 `local-data-platform/scripts/quality/read-only-gitsync-spark-provenance.sh` 增加以下拒绝条件：
- `REPORT_DIR` 必须是绝对路径，不能直接是符号链接，也不能位于当前 Git checkout 下；脚本设置 `umask 077` 后再创建目录。
- Airflow 返回零 Pod 时必须 `HOLD`，不允许将 ConfigMap 匹配误认成整体来源验证成功。
- Spark ConfigMap metadata.name 与明确指定名称不一致时必须 `HOLD`。
- 静态 Workflow 只执行 `bash -n` 和脚本源检查，不调用 kubectl；核实只有两个 Kubernetes 命令，均为带 context/namespace 的 get。

此修订仍未调用集群、没有执行任何 DAG 或 SparkApplication，也不确认 GitSync checkout SHA、实际 DAG 文件映射、Spark Driver `__file__`。原始 JSON 可能包含敏感信息，仍不可提交或分享。探针运行须具备只读角色及明确目标。Task 4.9 HOLD。
