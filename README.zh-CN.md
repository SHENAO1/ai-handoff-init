# ai-handoff-init

[English](README.md) | 简体中文

> 为 Claude Code、Codex CLI、GitHub Copilot，以及任何会读取 `CLAUDE.md` / `AGENTS.md` / `.github/copilot-instructions.md` 的助手，提供一键初始化的共享项目上下文体系。

[![Version: 0.3.0](https://img.shields.io/badge/version-0.3.0-blue.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 这是什么

这是一个跨 AI 编码助手的项目上下文初始化工具。

它会在目标项目里创建一套统一的共享记忆结构，让 Claude Code、Codex CLI、GitHub Copilot 在切换使用时，都能读取同一份项目状态、架构说明、决策记录和交接日志，而不是每次都重新解释一遍项目。

## 它解决什么问题

很多人在不同 AI 编码助手之间来回切换：

- **Claude Code** 读取 `CLAUDE.md`
- **Codex CLI** 读取 `AGENTS.md`
- **GitHub Copilot** 读取 `.github/copilot-instructions.md`

切换助手时，最常见的问题不是“不会写代码”，而是上下文丢失：

- 新助手不知道项目现在做到哪一步
- 昨天做过的架构决策没有被继承
- 用户不得不重复介绍目标、目录结构、约束和下一步任务

`ai-handoff-init` 的作用，就是把这些信息沉淀成一套稳定、通用、低维护成本的 Markdown 约定。

## 它会创建什么

脚本会在你的项目根目录下生成如下结构：

```text
your-project/
├── CLAUDE.md                          # 薄入口，<20 行，指向 .ai-context/
├── AGENTS.md                          # 薄入口，<20 行，指向 .ai-context/
├── .github/
│   └── copilot-instructions.md        # 薄入口，<20 行，指向 .ai-context/
└── .ai-context/                       # ← 共享上下文主目录
    ├── README.md
    ├── 00-overview.md                 # 目标、范围、成功标准（偏静态）
    ├── 01-architecture.md             # 模块、数据流、技术栈（偏静态）
    ├── 02-conventions.md              # 代码风格、命名、自主边界（偏静态）
    ├── 03-glossary.md                 # 术语表（半静态）
    ├── 04-decisions.md                # 架构决策记录（追加式）
    ├── 05-current-state.md            # 当前状态：已完成 / 进行中 / 下一步（动态）
    ├── 06-session-log.md              # 交接日志，最新在顶部（动态）
    └── 07-known-issues.md             # 已知问题与规避方式
```

所有助手都遵守同一套三条规则：

1. **进入会话时**：先看 `05-current-state.md` 和 `06-session-log.md` 顶部最新一条。
2. **结束会话时**：更新 `05`，并在 `06` 顶部追加新的交接记录。
3. **做出架构 / 依赖 / 技术选择决策时**：把原因和结论记到 `04-decisions.md`。

默认自主边界写在 `02-conventions.md`：助手在边界内应直接执行，只有越界、高风险或无法从仓库确认的事实才先问用户。

每次完成用户请求后，助手应给出简短最终回复，说明做了什么、改了哪些文件、跑了什么验证、剩余风险或下一步。最终回复面向用户；`06-session-log.md` 是给下一位助手的交接 baton。

没有守护进程，没有数据库，没有额外服务。只是所有助手都能读懂的一套 Markdown 约定。

## 安装与使用

这是一个 [Claude Skill](https://code.claude.com/docs/en/skills)，但你也可以完全脱离 Claude 单独运行脚本。

### 方式 A：作为 Claude Skill 使用

```bash
# 在你的 Claude skills 目录中
git clone https://github.com/<your-username>/ai-handoff-init.git
```

然后在任意项目里对 Claude 说“初始化 AI 上下文”或“init ai handoff”，它就会收集参数并调用初始化脚本。

### 方式 B：直接运行脚本

不依赖 Claude。把这个仓库 clone 到任意位置后，在你的目标项目目录里执行：

```bash
cd /path/to/your-project
python /path/to/ai-handoff-init/scripts/init.py \
  --name "my-project" \
  --description "A short one-liner" \
  --stack "Python 3.11,FastAPI,PostgreSQL" \
  --stage new \
  --as claude
```

如果你想走交互式流程，也可以直接运行：

```bash
python /path/to/ai-handoff-init/scripts/init.py
```

## Windows / PowerShell 最小可运行示例

如果你在 Windows 上做一次隔离冒烟测试，推荐先用系统临时目录，而不是直接在仓库根目录里跑：

```powershell
$tmp = Join-Path $env:TEMP 'ai-handoff-smoke'
if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

python .\scripts\init.py --target $tmp --dry-run --name demo --description x --stage new --as claude
python .\scripts\init.py --target $tmp --name demo --description x --stage new --as claude
```

如果你想体验完整交互式提问顺序，可以只带 `--dry-run`：

```powershell
$tmp = Join-Path $env:TEMP 'ai-handoff-smoke'
python .\scripts\init.py --target $tmp --dry-run
```

推荐关注这几个点：

- 提问顺序是否符合预期
- `--dry-run` 是否只打印计划、不写文件
- 真跑时是否输出 12 个目标文件

## CLI 参考

```text
python scripts/init.py [options]

  --target PATH         要初始化的项目根目录（默认：当前目录）
  --name NAME           项目名
  --description TEXT    一句描述
  --stack LIST          逗号分隔的技术栈（例如 "Python,FastAPI"）
  --stage {new,existing}  新项目还是已有项目
  --domains LIST        逗号分隔的术语包关键词（可选）
                        内置：web, ml, gnss-sdr
  --as {claude,codex,copilot}  当前是谁在运行 init
  --force               覆盖入口文件（自动创建 .bak-* 备份）
                        不会覆盖已有 .ai-context/
  --merge               只创建 .ai-context/，不覆盖入口文件
                        会打印需要手动粘贴的片段
  --adopt               收编已有 AI 入口文件到 .ai-context/，
                        将旧文件移动到 .ai-context/adopted-entry-backups/，
                        并写入新的标准入口文件
  --print-snippets      只渲染并打印入口文件片段，不写任何文件
  --dry-run             只展示计划，不写文件
  --doctor              只读检查已有 .ai-context/
  --upgrade             保守升级已有 .ai-context/
  --list-packs          列出可用术语包并退出
  --version             显示版本并退出
  --help                显示帮助
```

## 维护已有上下文

如果项目已经有 `.ai-context/`，可以先用 `--doctor` 检查是否符合当前协议：

```bash
python scripts/init.py --doctor --target /path/to/your-project
```

如果需要把旧上下文补齐到当前协议，用 `--upgrade`。推荐先预览：

```bash
python scripts/init.py --upgrade --target /path/to/your-project --dry-run
python scripts/init.py --upgrade --target /path/to/your-project
```

升级模式会在写入前为被修改文件创建 `.bak-YYYYMMDD-HHMMSS` 备份，并且不会重写会话历史。

## 推荐验证方式

如果你改了 CLI 或想确认初始化流程没坏，推荐至少跑这几条命令：

```powershell
python .\scripts\init.py --list-packs
python .\scripts\init.py --target $tmp --dry-run --name demo --description x --stage new --as claude --domains "foo,bar"
python .\scripts\init.py --doctor --target $tmp
python .\scripts\init.py --upgrade --target $tmp --dry-run
python .\scripts\init.py --target E:\definitely-not-here-xyz --name demo --description x --stage new --as claude
```

预期行为：

- `--list-packs` 会列出当前内置术语包
- `--domains "foo,bar"` 会打印一条 `info:`，表示没有任何关键词命中内置 pack
- `--doctor` 对符合当前协议的项目返回通过
- `--upgrade --dry-run` 只打印计划、不写文件
- 错误的 `--target` 会立刻报错，不会先进入交互提问

## 已有项目与冲突处理

如果项目里已经有 `CLAUDE.md`、`AGENTS.md`、`AGENT.md` 或 `.github/copilot-instructions.md`，但还没有 `.ai-context/`，有两条安全路径。

如果你希望 ai-handoff-init 接管入口文件，同时保留旧规则，推荐使用 `--adopt`：

```bash
python scripts/init.py --adopt ...
```

脚本会：

- 把旧入口文件原文导入 `.ai-context/09-adopted-instructions.md`
- 将旧入口文件移动到 `.ai-context/adopted-entry-backups/<timestamp>/`
- 在原路径写入新的标准入口文件
- 在 `05-current-state.md` 和 `06-session-log.md` 记录这次收编操作

如果你希望完全手动融合，使用 `--merge`：

```bash
python scripts/init.py --merge ...
```

脚本会：

- 只创建 `.ai-context/`
- 保留你已有的入口文件
- 打印应该粘贴到现有 `CLAUDE.md` / `AGENTS.md` / `.github/copilot-instructions.md` 里的片段

这样不会直接覆盖你已经手写过的项目入口说明。

如果项目里已经有 `.ai-context/`，不要用 `--merge`，因为 `--merge` 的职责是创建 `.ai-context/`。这种情况请使用 `--print-snippets`：

```bash
python scripts/init.py --print-snippets ...
```

它只会渲染并打印 `CLAUDE.md` / `AGENTS.md` / `.github/copilot-instructions.md` 三段入口内容，不创建、覆盖或备份任何文件。

如果你明确要覆盖现有入口文件，可以改用 `--force`。脚本会先生成 `.bak-时间戳` 备份，再写入新的入口文件；但它依然不会覆盖已有 `.ai-context/`。

## Glossary packs（术语包）

如果你的项目有明显的领域术语，可以通过 `--domains` 预填 `03-glossary.md`。

当前内置 pack：

- `web`：REST、GraphQL、SSR、hydration、CORS、JWT、ORM 等
- `ml`：epoch、batch size、overfitting、regularization、checkpoint 等
- `gnss-sdr`：BOC、Gold code、PCPS、PRN、Doppler、USRP 等

示例：

```bash
python scripts/init.py --domains "web,ml"
```

这会把两个 pack 都注入到术语表里。

你也可以列出当前支持的 pack：

```bash
python scripts/init.py --list-packs
```

如果你传入了未知关键词：

- 部分命中：未知项会被静默忽略
- 全部未命中：会额外打印一条 `info:` 提示

如果你想为自己的领域增加 pack，请看 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 设计原则

1. **入口文件薄、上下文目录厚**：`CLAUDE.md` / `AGENTS.md` / `.github/copilot-instructions.md` 都尽量控制在 20 行以内，把真正内容放进 `.ai-context/`。
2. **优先利用 Claude Code 的 `@` 能力**：`CLAUDE.md` 会直接引用 `@.ai-context/05-current-state.md`，让 Claude 自动带入当前状态；Codex 和 Copilot 不支持这个能力，所以靠文字规则补足。
3. **动态文件要小**：`05-current-state.md` 是快照，不是日志；`06-session-log.md` 只保留最近 20 条，避免 Claude Code 上下文超长。
4. **自主边界显式化**：`02-conventions.md` 说明助手可以直接做什么、什么必须先问，减少无意义请示，同时避免高风险静默改动。
5. **用户可见的完成回报**：助手结束实质性工作时要说明完成内容、改动文件、验证和下一步风险；它补充但不替代交接日志。
6. **不绑 Git 工作流**：脚本不会写 `.gitignore`，是否提交 `.ai-context/` 由项目自行决定。
7. **术语包是可选扩展**：默认不绑定任何行业，只有在你明确传 `--domains` 时才会注入特定领域术语。

## 许可证

MIT。见 [LICENSE](LICENSE)。

## 贡献

如何添加 glossary pack、调整模板或查看提交流程，请见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 变更记录

见 [CHANGELOG.md](CHANGELOG.md)。
