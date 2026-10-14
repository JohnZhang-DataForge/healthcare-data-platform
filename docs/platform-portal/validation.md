# Portal — 实际验收记录（Live 证据总览）

## 已确认

- PostgreSQL14 `dw-postgre14`：用户实测 Postgres 14.24，DB/Role 均 `marquez`；50Gi `postgres-marquez` Retain PVC，worker03 原路径 `/data/postgres-marquez/...`；EndpointSlice 服务 5432 已连 Pod。**未进行重新安装**。
- 上轮 [Run 38497309444](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497309444)：确认 PG14 版本、Port 30999 空闲，创建 `dw-marquez` Namespace 与独立 DB Secret。**没有创建 Marquez API/Web**。
- [Run 38497221548](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497221548) 失败：Runner 缺 Helm。
- [Run 38497309444](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497309444) 失败：错误的 Chart index URL 404。
- [Run 38497455412](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497455412) 失败：Bash 文本生成破损，安装没有开始。

## 待真实验收

Marquez Chart 静态验收 / Helm API Web / PG14 Schema 迁移 / HTTP API-Web / Web-only NodePort 30999 / 实际 OpenLineage 接入均待新 Runner Run 证明。本文件不得写虚假的 PASS，后续 Live Closeout 必须含完整 SHA/Run/PR 和真实 API、数据库证据。

历史证据：见 [历史归档](./archive/2026-10-13/README.md)。
