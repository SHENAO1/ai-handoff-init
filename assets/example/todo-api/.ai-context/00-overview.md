# 00 · 项目概览

<!-- 静态文档。范围或目标发生重大变更时才修订。 -->

## 项目名称
todo-api

## 一句话描述
RESTful API for personal todo lists

## 项目目标
- 提供最小可用的 todo 增删改查 REST API,练手 FastAPI 与 SQLAlchemy 2.0
- 支持多用户(JWT 鉴权)、列表分组、到期提醒
- 为后续前端(Next.js)提供稳定契约

## 范围边界

### 本项目做什么(In scope)
- REST API:todo 资源的 CRUD、list 分组、用户注册/登录
- PostgreSQL 持久化,Alembic 迁移
- OpenAPI schema 自动生成

### 本项目不做什么(Out of scope)
- 前端(另起一个 repo)
- 推送通知(初版只做 API,提醒以 GET endpoint 返回到期列表)
- 多租户隔离、企业级权限
- 搜索、全文检索

## 成功标准
- [ ] 所有 endpoint 通过 OpenAPI 自动生成客户端可成功调用
- [ ] 单元测试覆盖率 > 80%
- [ ] p95 延迟在本地 docker compose 环境下 < 50ms
- [ ] `docker compose up` 一键启动(含 Postgres)

## 相关资源
- FastAPI docs: https://fastapi.tiangolo.com/
- SQLAlchemy 2.0 style: https://docs.sqlalchemy.org/en/20/
