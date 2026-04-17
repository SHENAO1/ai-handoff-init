# 02 · 代码与协作约定

<!-- 静态文档。团队约定变更时更新。 -->

## 代码风格
- `ruff format` + `ruff check` — 行宽 100
- 类型标注:所有 public 函数必须有返回类型
- docstring:只对 public API 与复杂逻辑写;不要给 getter/setter 写 "Returns the foo."

## 命名约定
- 模块/文件:`snake_case.py`
- 类:`PascalCase`
- 函数/变量:`snake_case`
- 常量:`UPPER_SNAKE`
- SQLAlchemy models:单数(`Todo`,不是 `Todos`);表名复数(`__tablename__ = "todos"`)

## 目录约定
- HTTP 层代码只放 `app/api/`,不写业务逻辑
- 业务逻辑放 service 函数(暂未拆目录,等 endpoint > 10 个再拆 `app/services/`)
- 测试文件与被测模块同名加 `test_` 前缀

## 提交与分支
- Conventional Commits:`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- 主分支 `main`,功能分支 `feat/xxx`,修复分支 `fix/xxx`
- 禁止直推 main,必须 PR 走 CI

## 测试策略
- 单元测试:纯函数,mock 数据库
- 集成测试:真实 Postgres(docker compose 起的那个),事务包裹回滚
- 目标覆盖率 80%,CI 失败阈值 75%
- 命令:`pytest`、`pytest --cov`

## AI 助手协作约定
- 改动超过 50 行或涉及跨模块时先在 `04-decisions.md` 留记录
- 新增依赖前先检查 `01-architecture.md` 是否已有同类项
- 遇到阻塞写进 `07-known-issues.md`,不要悄悄绕过
- 不确定的事实必须在 `.ai-context/` 中查证后再写进代码或回复
- 不要主动跑 `alembic upgrade head` — 迁移由人手动审核
