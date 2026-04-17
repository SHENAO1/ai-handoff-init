# 01 · 架构与技术栈

<!-- 静态文档。重大重构时更新。 -->

## 技术栈
- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL

## 模块划分

| 模块 | 职责 | 关键入口文件 |
| --- | --- | --- |
| `app/main.py` | FastAPI 应用实例、lifespan、路由挂载 | `app/main.py` |
| `app/api/` | HTTP 层:路由、依赖注入、Pydantic schema | `app/api/todos.py`, `app/api/users.py` |
| `app/db/` | SQLAlchemy 2.0 models 与 session 工厂 | `app/db/models.py`, `app/db/session.py` |
| `app/auth/` | JWT 签发与校验 | `app/auth/jwt.py` |
| `alembic/` | schema 迁移脚本 | `alembic/versions/` |
| `tests/` | pytest 单元 + 集成测试 | `tests/conftest.py` |

## 数据流

```
HTTP request
    → FastAPI router (app/api/*)
    → Pydantic validation
    → auth dependency (JWT decode, 注入 current_user)
    → service function
    → SQLAlchemy session (app/db/session.py)
    → PostgreSQL
    ← ORM object
    ← Pydantic response_model 序列化
    ← HTTP response
```

## 依赖与外部服务
- PostgreSQL 15(docker compose 本地,生产环境 RDS)
- 无外部 HTTP 服务依赖

## 构建与运行

```bash
# 启动数据库 + 应用
docker compose up -d

# 只跑应用(需本地 Postgres)
uvicorn app.main:app --reload

# 跑迁移
alembic upgrade head

# 跑测试
pytest
```

## 目录结构

```text
.
├── alembic/
│   ├── versions/
│   └── env.py
├── app/
│   ├── api/
│   │   ├── todos.py
│   │   └── users.py
│   ├── auth/
│   │   └── jwt.py
│   ├── db/
│   │   ├── models.py
│   │   └── session.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_todos.py
│   └── test_auth.py
├── docker-compose.yml
├── pyproject.toml
└── .ai-context/   ← 你在这儿
```
