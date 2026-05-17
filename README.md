# ai-handoff-init

English | [简体中文](README.zh-CN.md)

> One-command cross-assistant project context bootstrapper for Claude Code, Codex CLI, GitHub Copilot, and anything else that reads `CLAUDE.md` / `AGENTS.md` / `.github/copilot-instructions.md`.
>
> 一键初始化跨 AI 编码助手的共享项目上下文体系。

[![Version: 0.3.0](https://img.shields.io/badge/version-0.3.0-blue.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## The problem

You're rotating between three AI coding assistants because quota / strengths / IDE coverage differ:

- **Claude Code** reads `CLAUDE.md`
- **Codex CLI** reads `AGENTS.md`
- **GitHub Copilot** reads `.github/copilot-instructions.md`

Every time you switch assistants, context is lost. You re-explain the project. Decisions from yesterday's session vanish. The new assistant has no idea what's in progress.

## What this does

Creates a canonical, shared memory layout that **all three assistants read from**:

```
your-project/
├── CLAUDE.md                          # thin entry, <20 lines, points to .ai-context/
├── AGENTS.md                          # thin entry, <20 lines, points to .ai-context/
├── .github/
│   └── copilot-instructions.md        # thin entry, <20 lines, points to .ai-context/
└── .ai-context/                       # ← the shared brain
    ├── README.md
    ├── 00-overview.md                 # goals, scope, success criteria (static)
    ├── 01-architecture.md             # modules, data flow, stack (static)
    ├── 02-conventions.md              # code style, autonomy policy (static)
    ├── 03-glossary.md                 # domain terms (semi-static)
    ├── 04-decisions.md                # ADR log (append-only)
    ├── 05-current-state.md            # done / in-progress / next (DYNAMIC)
    ├── 06-session-log.md              # handoff journal, newest on top (DYNAMIC)
    └── 07-known-issues.md             # pitfalls + workarounds
```

Three rules every assistant follows (embedded in every entry file):

1. **Entering a session** → read `05-current-state.md` and the top entry of `06-session-log.md`.
2. **Leaving a session** → update `05`, prepend a new entry to `06`.
3. **Architectural/dependency/tech-choice decision** → append to `04-decisions.md`.

The default autonomy boundary lives in `02-conventions.md`: assistants should act directly inside that boundary, and ask first only for out-of-bounds, high-risk, or unverified facts that cannot be resolved from the repository.

After completing a user request, assistants should give a concise final report covering what was done, changed files, validation, and remaining risks or next steps. That final reply is for the user; `06-session-log.md` is the baton for the next assistant.

That's it. No magic. No daemon. No API calls. Just markdown conventions that any assistant — or any human — can follow.

## Installation

This is a [Claude Skill](https://code.claude.com/docs/en/skills). Two ways to use it:

### Option A — Use as a Skill with Claude Code

```bash
# In your Claude skills directory
git clone https://github.com/<your-username>/ai-handoff-init.git
```

Then in any project, tell Claude: *"初始化 AI 上下文"* or *"init ai handoff"*. Claude will ask you a few questions and run the init script.

### Option B — Run the script directly

No Claude needed. Clone this repo anywhere, then:

```bash
cd /path/to/your-project
python /path/to/ai-handoff-init/scripts/init.py \
  --name "my-project" \
  --description "A short one-liner" \
  --stack "Python 3.11,FastAPI,PostgreSQL" \
  --stage new \
  --as claude
```

Or run with no args for interactive prompts:

```bash
python /path/to/ai-handoff-init/scripts/init.py
```

## CLI reference

```
python scripts/init.py [options]

  --target PATH         Project root to initialize (default: current dir)
  --name NAME           Project name
  --description TEXT    One-sentence description
  --stack LIST          Comma-separated tech stack (e.g. "Python,FastAPI")
  --stage {new,existing}  Whether this is a fresh repo or has code already
  --domains LIST        Comma-separated glossary pack keywords (optional)
                        Built-in packs: web, ml, gnss-sdr
  --as {claude,codex,copilot}  Which assistant is running init
  --force               Overwrite entry files (auto-backup as .bak-*)
                        Will NOT overwrite existing .ai-context/
  --merge               Only create .ai-context/, leave entry files alone
                        (prints snippets for you to paste manually)
  --adopt               Import existing AI entry files into .ai-context/,
                        move originals to .ai-context/adopted-entry-backups/,
                        and write fresh generated entry files
  --print-snippets      Print rendered entry-file snippets only; write no files
  --dry-run             Show plan without writing files
  --doctor              Check an existing .ai-context/ without writing files
  --upgrade             Conservatively upgrade an existing .ai-context/
  --list-packs          List available glossary packs and exit
  --version             Show version and exit
  --help                Show this message
```

## Maintaining existing context

Use `--doctor` when a project already has `.ai-context/` and you want to check whether it matches the current protocol:

```bash
python scripts/init.py --doctor --target /path/to/your-project
```

Use `--upgrade` to conservatively add missing protocol rules to an existing context. Preview first:

```bash
python scripts/init.py --upgrade --target /path/to/your-project --dry-run
python scripts/init.py --upgrade --target /path/to/your-project
```

Upgrade mode creates `.bak-YYYYMMDD-HHMMSS` backups for files it changes and does not rewrite session history.

## Existing projects and conflicts

If your project already has `CLAUDE.md`, `AGENTS.md`, `AGENT.md`, or `.github/copilot-instructions.md` but does **not** yet have `.ai-context/`, choose one of two safe paths:

- Use `--adopt` when you want ai-handoff-init to take over the entry files while preserving the old instructions. The script imports the old content into `.ai-context/09-adopted-instructions.md`, moves the original files into `.ai-context/adopted-entry-backups/<timestamp>/`, writes fresh generated entry files, and records the operation in `05-current-state.md` / `06-session-log.md`.
- Use `--merge` when you want a fully manual merge. The script creates `.ai-context/` and prints the snippets you need to add to your existing entry files.

If your project already has `.ai-context/`, use `--print-snippets` instead. It only renders and prints the `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md` snippets. It does not create, overwrite, or back up any files.

Use `--force` only when you explicitly want to overwrite existing entry files. It creates `.bak-YYYYMMDD-HHMMSS` backups first, but still refuses to overwrite an existing `.ai-context/`.

## Glossary packs

If your project has a non-obvious domain vocabulary, pre-fill the glossary with one of:

- `web` — REST, GraphQL, SSR, hydration, CORS, JWT, ORM, etc.
- `ml` — epoch, batch size, overfitting, regularization, checkpoint, etc.
- `gnss-sdr` — BOC, Gold code, PCPS, PRN, Doppler, USRP, etc.

Example: `--domains "web,ml"` injects both packs.

Run `python scripts/init.py --list-packs` to see the current list grouped by file (aliases like `gnss` / `sdr` → `gnss-sdr.md` are shown together). Unknown keywords are ignored silently; if **none** of the keywords you pass match a pack, the script prints one heads-up on stderr.

Useful maintenance smoke tests:

```powershell
python .\scripts\init.py --doctor --target $tmp
python .\scripts\init.py --upgrade --target $tmp --dry-run
```

Want a pack for your domain? See [CONTRIBUTING.md](CONTRIBUTING.md).

## Design principles

1. **Thin entry files, fat context directory** — `CLAUDE.md` et al. stay under 20 lines to respect Copilot's "short instructions" and Codex's `project_doc_max_bytes` limits. All substance lives in `.ai-context/`.
2. **Claude Code uses `@` references** — `CLAUDE.md` includes `@.ai-context/05-current-state.md` so Claude auto-loads the state file. Codex and Copilot don't support `@`; they rely on prose instructions.
3. **Dynamic files stay small** — `05-current-state.md` is a snapshot, not a log. `06-session-log.md` is capped at 20 recent entries (older ones archive to `06-session-log-archive.md`) to avoid hitting Claude Code's 40,000-char memory limit.
4. **Autonomy is explicit** — `02-conventions.md` defines what assistants can do directly and what requires user confirmation, so handoffs preserve momentum without hiding risky changes.
5. **User-facing completion reports** — assistants end substantive work by summarizing done work, changed files, validation, and next risks; this complements, but does not replace, the handoff log.
6. **Git-agnostic** — we don't write a `.gitignore`. See `.ai-context/README.md` for commit strategy guidance.
7. **Domain extensibility** — glossary packs are opt-in, mechanism > content. The skill is domain-neutral by default.

## License

MIT. See [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a glossary pack or propose template changes.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
