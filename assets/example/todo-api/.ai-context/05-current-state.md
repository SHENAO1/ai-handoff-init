# 05 · 当前状态

<!-- 动态文档。代码、计划、状态或结论变化时更新。保持短小。 -->

**最近更新**: 2026-04-18

## 🎯 Current Goal
- 完成 todos 路由的写入/读取/删除能力,并把测试覆盖率先拉到 60%

## ✅ Done
- `.ai-context/` 骨架已建立(由 Claude Code 初始化)
- `00-overview.md` 与 `01-architecture.md` 已填充项目目标与模块划分
- SQLAlchemy 2.0 风格选型已敲定(见 `04-decisions.md` 2026-04-18 条目)
- `app/db/models.py` 首版 `User` / `Todo` / `TodoList` 三个 model 已实现
- `alembic init` + 首次迁移 `0001_initial.py` 已生成并本地应用成功

## 🚧 In Progress
- `app/api/todos.py`:GET /todos 路由已写完,POST /todos 写到一半
- `tests/test_todos.py`:conftest fixture 已写,测试用例待补

## ⏭️ Next Exact Step
- 补完 `POST /todos`,加 Pydantic schema `TodoCreate`
- 写 `GET /todos/{id}` 与 `DELETE /todos/{id}`
- JWT 鉴权依赖(`app/auth/jwt.py`)接入 todos 路由
- 测试覆盖率先拉到 60%

## 🧪 Validation Command
```bash
pytest tests/test_todos.py
```

## 🤖 Autonomy Notes
- 可以直接补 endpoint、schema、fixture 和测试。
- 不要主动跑 `alembic upgrade head`;数据库迁移由人手动审核。
- 如果需要改公开 API、数据模型或迁移文件,先向用户确认。

## ⚠️ Blocked
- (暂无)
