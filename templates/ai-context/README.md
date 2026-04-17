# .ai-context/ — 跨助手项目上下文

本目录是一套面向多个 AI 编码助手(Claude Code、Codex CLI、GitHub Copilot 等)的共享记忆。
项目根目录下的 `CLAUDE.md`、`AGENTS.md`、`.github/copilot-instructions.md` 是各助手的入口,
它们都指向本目录。

## 文件导航

| 文件 | 性质 | 用途 |
| --- | --- | --- |
| `00-overview.md` | 静态 | 项目目标、范围、成功标准 |
| `01-architecture.md` | 静态 | 模块、数据流、技术栈 |
| `02-conventions.md` | 静态 | 代码风格、命名、目录约定 |
| `03-glossary.md` | 准静态 | 领域术语表 |
| `04-decisions.md` | 追加型 | ADR 风格决策日志(带日期) |
| `05-current-state.md` | **动态** | done / in-progress / next |
| `06-session-log.md` | **动态** | 倒序追加的会话交接日志 |
| `07-known-issues.md` | 准静态 | 已知问题与 workaround |

## 三条铁律(每个助手都必须遵守)

1. **进入会话**:先读 `05-current-state.md` 和 `06-session-log.md` 最上面一条。
2. **结束会话**:更新 `05-current-state.md`,并在 `06-session-log.md` **顶部**追加一条新条目。
3. **关键决策**:架构、依赖、技术选型的决定写入 `04-decisions.md`,带日期与理由。

## 维护原则

- 静态文件(`00` ~ `02`)只在范围或结构发生重大变更时修订。
- 追加型文件(`04`、`06`)不删除历史条目,作废用标注替代。
- 动态文件(`05`、`06`)每次会话都应触动。
- `06-session-log.md` 超过 20 条时,把较早的一半归档到 `06-session-log-archive.md`。

## Git 策略建议

本目录是否进入版本控制,取决于团队场景:

- **个人项目 / 信任的小团队**:全部提交,包括 `05` 和 `06`。这样队友和新加入的 AI 助手能看到完整交接历史。推荐做法。
- **不希望公开交接细节**:把 `05-current-state.md` 和 `06-session-log.md` 加入 `.gitignore`。代价是 handoff 退化为"单人跨机器",失去多人共享价值。
- **团队但怕合并冲突**:提交全部文件,但在 `.gitattributes` 中标记 `.ai-context/06-*.md merge=ours`(或 `theirs`),避免逐行合并。

本 skill 不替你做决定。默认 `git add .ai-context/` 即可。
