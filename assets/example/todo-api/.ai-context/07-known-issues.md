# 07 · 已知问题与 Workaround

<!-- 准静态文档。遇到坑就记,解决了在条目下标注"已解决"而非删除。 -->

> **条目格式**:
>
> ### 问题标题
> - **症状**:
> - **定位**:
> - **Workaround**:
> - **状态**: 待解决 / 已解决(YYYY-MM-DD)

---

### Alembic autogenerate 跑出空迁移
- **症状**: 修改了 `app/db/models.py` 里的字段,但 `alembic revision --autogenerate -m "..."` 生成的迁移 upgrade/downgrade 都是空的。
- **定位**: `alembic/env.py` 的 `target_metadata` 没指向实际的 `Base.metadata`——模板里默认是 `None`。
- **Workaround**: 在 `env.py` 顶部加 `from app.db.models import Base` 然后设 `target_metadata = Base.metadata`。
- **状态**: 已解决(2026-04-18)
