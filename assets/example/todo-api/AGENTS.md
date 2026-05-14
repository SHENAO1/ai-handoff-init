<!-- 本文件是 Codex CLI(及其他读 AGENTS.md 的助手)的项目入口。由 ai-handoff-init 生成。 -->

你是 **Codex**,正在参与项目 **todo-api**:RESTful API for personal todo lists

**技术栈**: Python 3.11, FastAPI, SQLAlchemy, PostgreSQL

## 默认工作方式
在 `.ai-context/02-conventions.md` 的 AI Autonomy Policy 边界内,优先直接执行用户请求;只有越界、高风险或事实无法从仓库确认时才先问。
完成用户请求后,用简短最终回复汇报 Done / Changed files / Validation / Next or risks。

## 会话交接三条铁律(不可协商)
1. **进入会话**:先读 `.ai-context/05-current-state.md` 和 `.ai-context/06-session-log.md` 最上面一条。
2. **结束会话**:更新 `.ai-context/05-current-state.md`,并在 `.ai-context/06-session-log.md` **顶部**追加一条新条目。
3. **关键决策**:架构/依赖/技术选型写入 `.ai-context/04-decisions.md`,带日期与理由。

完整导航与 Git 策略见 `.ai-context/README.md`。本项目同时通过 `CLAUDE.md`(Claude Code)和 `.github/copilot-instructions.md`(Copilot)被其他助手使用,三者共享 `.ai-context/`。
