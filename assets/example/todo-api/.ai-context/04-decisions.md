# 04 · 决策日志(ADR)

<!-- 追加型文档。每次做出架构/技术/流程上的决策,在顶部加一条。 -->

> 删除决策 = 删历史。作废的决策写"推翻先前决策(见 YYYY-MM-DD 条目)"而不是移除。

## 模板(复制使用)

```markdown
## YYYY-MM-DD · 决策标题

**背景**: 为什么需要做这个决定?触发事件是什么?

**选项**:
- A: ...
- B: ...

**决策**: 选择 X。

**理由**: ...

**影响**: 哪些文件/模块会被改?哪些约定被确立?

**状态**: 生效 / 已推翻(见 YYYY-MM-DD)
```

---

## 2026-04-18 · 使用 SQLAlchemy 2.0 的 Mapped/relationship 风格而不是 1.x legacy

**背景**: 初始化模型时发现 FastAPI 教程多数仍用 SQLAlchemy 1.4 语法(`Column` + `declarative_base()`),但 2.0 已经是默认版本。选哪个风格会影响后续所有 models。

**选项**:
- A: 1.4 legacy 风格(`Column(Integer, primary_key=True)`)
- B: 2.0 typed 风格(`mapped_column` + `Mapped[int]`)

**决策**: 选 B。

**理由**: 2.0 风格原生支持类型标注,与 FastAPI + Pydantic 的类型友好度更高;IDE 补全更好;新代码没理由用 legacy API。

**影响**:
- 所有 `app/db/models.py` 用 `Mapped[...]` + `mapped_column(...)` 定义字段
- `pyproject.toml` 锁 `sqlalchemy >= 2.0,<3`
- `02-conventions.md` 已更新 SQLAlchemy 风格约定

**状态**: 生效
