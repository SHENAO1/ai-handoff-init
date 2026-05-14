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
### AI Autonomy Policy

- 默认行动优先:用户要求实现、修复、整理或验证时,在下列边界内直接推进,不要把普通执行变成反复请示。
- 可以直接执行:
  - 阅读、搜索和总结仓库文件。
  - 运行 `pytest`、`ruff format`、`ruff check`、类型检查和只读诊断命令。
  - 按现有 FastAPI / SQLAlchemy 模式完成小范围 endpoint、schema、测试和文档更新。
  - 更新与本次工作直接相关的 `.ai-context/` 状态、验证记录和交接日志。
- 必须先确认:
  - 删除或迁移大量文件、执行不可逆操作、重写提交历史。
  - 改公开 API、数据模型、迁移策略、认证授权、安全边界或发布流程。
  - 新增生产依赖、外部服务、付费资源、云权限或会影响部署环境的配置。
  - 处理密钥、生产数据、用户隐私数据,或需要联网访问非公开系统。
  - 运行 `alembic upgrade head` 或改已发布迁移;迁移由人手动审核。
- 记录规则:
  - 普通代码改动不因行数触发 ADR。
  - 只有架构、依赖、公开接口、数据模型、长期流程约定变化时,才在 `04-decisions.md` 记录原因和影响。
  - 遇到阻塞写进 `07-known-issues.md`,不要悄悄绕过。
  - 不确定的事实先从仓库、测试、文档或 `.ai-context/` 查证;查不到且继续执行会带来明显风险时再询问用户。

### Completion Report / Definition of Done

- 在 AI Autonomy Policy 边界内的任务应直接完成,不要只给建议或计划。
- 若代码、计划、状态或结论变化,更新 `05-current-state.md`。
- 若发生可交接变化,在 `06-session-log.md` 顶部追加条目。
- 最终回复必须简短说明:Done / Changed files / Validation / Next or risks。
- `06-session-log.md` 是给下一位 AI 的 baton;最终回复是给用户的执行回报,两者不能互相替代。
