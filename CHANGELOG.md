# Changelog

本项目采用持续更新日志，记录功能变更、问题修复与运行状态变化。

## [Unreleased]

### Added

- 新增 SPEC 文档：SPEC.md
- 明确首轮目标为“跑通全链路（抓取数据 -> 构建索引 -> 启动服务 -> 完成一次 docs 问答）”
- 建立问题挖掘与迭代更新机制（SPEC + CHANGELOG 联动）
- 新增 pytest 配置与单元测试集（tests/unit）
- 新增模块：src/graph_routes.py（路由决策）
- 新增模块：src/feedback/store.py（反馈持久化）
- 新增模块：src/build_utils.py（构建目录解析）

### Changed

- 运行环境基线统一为 uv
- 验证命令统一为 uv run python <script>
- 修复 build.py 目录组装逻辑，避免 LEARN_DIR 未定义导致 NameError
- app.py 不再内嵌反馈 JSON 落盘逻辑，改为调用独立反馈存储模块
- src/graph.py 不再内嵌路由判定实现，改为调用独立路由模块

### Verified

- uv --version 可用
- uv run python --version 可用
- uv run python app.py 可启动 Gradio 服务

### Known Issues

- 索引构建被 API 拒绝：uv run python build.py 在向量化阶段返回 `status_code: 400 / code: Arrearage`
- 当前 data/faiss_db 未生成，docs 问答主链路尚未完成端到端验收
