---
name: ai-handoff-init
description: Initialize a shared cross-assistant project context system — creates `.ai-context/` directory with 9 structured Markdown files plus thin entry files for Claude Code (`CLAUDE.md`), Codex CLI (`AGENTS.md`), and GitHub Copilot (`.github/copilot-instructions.md`) so that multiple AI coding assistants share the same project memory and can hand off work without the user re-explaining context. Use this skill whenever the user says "初始化 AI 上下文", "创建 AI 交接文件", "init ai handoff", "跨助手上下文", "cross-assistant context", "set up project memory for Claude and Codex", or similar. Also trigger proactively when the user mentions juggling two or more AI coding assistants (any combination of Claude Code, Codex CLI, GitHub Copilot, Cursor, Cline, Gemini), complains about losing context when switching assistants, says they keep re-explaining the project, or starts a fresh repo while mentioning multiple assistants — even if they never say "initialize" or "skill". Recognize the intent, not just the keywords.
version: 0.3.0
---

# ai-handoff-init

Bootstraps a uniform, cross-assistant memory layout so Claude Code, Codex CLI, and GitHub Copilot (or any other assistant reading `CLAUDE.md` / `AGENTS.md` / `.github/copilot-instructions.md`) share the same project context.

## The problem this solves

A single user rotates between AI coding assistants — quota limits on one, better IDE integration from another, specialized strengths for particular tasks. Without shared memory, each assistant has to be re-briefed. Decisions get lost. "Current state" lives only in the user's head.

## What gets created

```
<project-root>/
├── CLAUDE.md                       # entry, < 20 lines, uses @ refs
├── AGENTS.md                       # entry, < 20 lines
├── .github/
│   └── copilot-instructions.md     # entry, < 20 lines
└── .ai-context/
    ├── README.md                   # navigation + git strategy notes
    ├── 00-overview.md              # goals, scope, success (static)
    ├── 01-architecture.md          # modules, data flow, stack (static)
    ├── 02-conventions.md           # style, naming, autonomy policy (static)
    ├── 03-glossary.md              # domain terms (semi-static)
    ├── 04-decisions.md             # ADR log (append-only, dated)
    ├── 05-current-state.md         # DYNAMIC — done / in-progress / next
    ├── 06-session-log.md           # DYNAMIC — handoff log, newest on top
    └── 07-known-issues.md          # pitfalls + workarounds
```

## When to trigger (and when NOT to)

**Trigger on:**

- Explicit phrases listed in the description.
- User mentions 2+ coding assistants and shared context would help.
- User complains about re-explaining projects across assistants.
- User starts a new repo while already known to rotate assistants.

**Do NOT trigger on:**

- User only uses one assistant and isn't asking for persistent memory.
- `.ai-context/` already exists in the target — offer to inspect/update via direct edits, don't re-initialize. If the user only needs assistant entry-file snippets for the existing context, run `--print-snippets`.
- Generic "write a README" requests — that's a different task.
- Generic Python/code questions that happen to mention an AI tool in passing.

## How to run this skill

The work is done by `scripts/init.py`. Always prefer the script over hand-writing the files — templating, glossary injection, and rotation metadata are easy to get wrong by hand.

### Step 1 — Collect inputs

Ask the user in one message (not five). If the conversation already answers any of these, just confirm, don't re-ask.

1. **Project name** (short slug, e.g. `todo-api`)
2. **One-sentence description**
3. **Primary tech stack** as a comma-separated list (e.g. `Python 3.11, FastAPI, PostgreSQL`)
4. **Current stage**: `new` (fresh repo) or `existing` (adding context to live code)
5. **Domain keywords** (optional, comma-separated): used to pre-fill the glossary. Built-in packs: `web`, `ml`, `gnss-sdr`. If the user names something else, it won't error — it just won't inject extra terms. Most projects can leave this empty.
6. **Which assistant is running init**: `claude`, `codex`, or `copilot`. If you (the assistant reading this) are running it, you already know — pass `--as <yours>`.

### Step 2 — Run the script

```bash
python scripts/init.py \
  --target <project-root> \
  --name "<project name>" \
  --description "<one sentence>" \
  --stack "Python 3.11,FastAPI,PostgreSQL" \
  --stage new \
  --domains "web" \
  --as claude
```

Prefer `--dry-run` first to show the plan before writing. Especially important if the target directory is not empty.

Interactive fallback: running `python scripts/init.py` with no args prompts for each field.

### Step 3 — Handle existing files and snippet-only output

If the project already has `CLAUDE.md`, `AGENTS.md`, `AGENT.md`, or `.github/copilot-instructions.md`:

- **Default**: script aborts and lists conflicts.
- `--force`: overwrites, but creates `.bak-YYYYMMDD-HHMMSS` backups first.
- `--adopt` (recommended when the user wants ai-handoff-init to take over existing entry files): imports old entry content into `.ai-context/09-adopted-instructions.md`, moves originals to `.ai-context/adopted-entry-backups/<timestamp>/`, writes fresh generated entry files, and records the operation in `05-current-state.md` / `06-session-log.md`.
- `--merge` (recommended when user has hand-written entry files and no `.ai-context/` yet): creates only `.ai-context/` and prints the snippets the user needs to add to their existing entry files.
- `--print-snippets` (recommended when `.ai-context/` already exists): renders and prints the `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md` snippets only. It writes no files, so it is the safe path when the target already has context files.
- `--doctor` (recommended before changing an existing context): checks whether `.ai-context/` and entry files match the current protocol without writing files.
- `--upgrade` (recommended for older contexts): conservatively inserts missing protocol guidance, creates backups before writes, and does not rewrite session history. Preview with `--upgrade --dry-run`.

Ask the user which mode they want if conflicts exist.

### Step 4 — If `--stage existing`, prefill 00 and 01

After init, the user's `00-overview.md` and `01-architecture.md` are empty templates. For an existing codebase, immediately:

1. Run `ls` or `tree -L 2` on the project root.
2. Read the project's `README.md` (if any) and the main entry file (`main.py`, `index.js`, `Cargo.toml`, etc.).
3. Prefill the TODO sections of `00-overview.md` (project goals, scope) and `01-architecture.md` (module list, tech stack details).

Don't ask the user to describe their own project — scan the code first.

### Step 5 — Confirm and orient

After the script succeeds:

1. Show the created file tree (the script prints it).
2. Remind the user of the three handoff rules (below).
3. Suggest the first substantive task: filling in project goals or starting real work.

## The three handoff rules

These are embedded in all three entry files and in `.ai-context/README.md`. Every assistant — including future you in the next session — must follow them:

1. **On session start**: read `.ai-context/05-current-state.md` and the top entry of `.ai-context/06-session-log.md`.
2. **On session end**: update `.ai-context/05-current-state.md`, then prepend a new entry to `.ai-context/06-session-log.md` using the canonical format.
3. **On architectural / dependency / tech-choice decisions**: append to `.ai-context/04-decisions.md` with date and rationale.

Default autonomy is defined in `.ai-context/02-conventions.md`: assistants should act directly inside the policy boundary, and ask first only for out-of-bounds, high-risk, or unverified facts that cannot be resolved from the repository.

After completing a user request, assistants should give a concise final report covering Done, Changed files, Validation, and Next or risks. That final reply is for the user; `06-session-log.md` is the baton for the next assistant, and the two do not replace each other.

## Canonical session log entry format

```markdown
## YYYY-MM-DD · <Assistant name>
**完成 / Done**: ...
**进行中 / In progress**: ...
**改动文件 / Changed files**: ...
**验证 / Validation**: ...
**剩余风险 / Remaining risk**: ...
**下一步建议 / Next**: ...
**注意 / Watch out**: ...
```

Newer entries go on top. When `06-session-log.md` exceeds 20 entries, archive the bottom half to `06-session-log-archive.md` (or `archive/YYYY-MM.md` for finer slicing). This keeps the active log under Claude Code's 40,000-character memory cap.

## Placeholders used in templates

| Placeholder | Example | Used in |
| --- | --- | --- |
| `{{PROJECT_NAME}}` | `todo-api` | all files |
| `{{DESCRIPTION}}` | `RESTful API for personal todo lists` | `00-overview.md`, entry files |
| `{{TECH_STACK_INLINE}}` | `Python 3.11, FastAPI, PostgreSQL` | entry files (one line) |
| `{{TECH_STACK_LIST}}` | `- Python 3.11\n- FastAPI\n- PostgreSQL` | `01-architecture.md` (Markdown list) |
| `{{INIT_DATE}}` | `2026-04-17` | `05`, `06` |
| `{{INIT_ASSISTANT}}` | `Claude Code` / `Codex` / `GitHub Copilot` | `05`, `06` |
| `{{CONTEXT_PROTOCOL_VERSION}}` | `0.3.0` | `.ai-context/README.md` |

## Domain glossary extension

Glossary packs live in `templates/glossary-packs/<pack>.md`. The script maps user-supplied keywords to pack filenames via the `GLOSSARY_PACKS` dict at the top of `scripts/init.py`:

```python
GLOSSARY_PACKS = {
    "web":      "web-fullstack.md",
    "ml":       "ml-basics.md",
    "gnss-sdr": "gnss-sdr.md",
    "gnss":     "gnss-sdr.md",
    "sdr":      "gnss-sdr.md",
}
```

Multiple matched packs are concatenated. Unmatched keywords are silently ignored (not an error — user may be noting a domain we don't have a pack for yet). To add a pack, see `CONTRIBUTING.md`.

Most projects don't need a pack. `--domains` is opt-in.

## Example

See `assets/example/todo-api/` for a fully-rendered example project (Python FastAPI todo API, `web` glossary pack applied). Use it to see what every file looks like after `init.py` runs.

## Design rationale (why it's built this way)

Read this if you're tempted to change the structure.

- **Thin entry files.** Copilot docs explicitly warn that long instruction files cause guidance to be overlooked. Codex has `project_doc_max_bytes`. Claude Code has a 40,000-char cap per memory file. Keeping entry files under 20 lines respects all three.
- **Substance in `.ai-context/`.** The entry files delegate to files that aren't auto-loaded into context — they're read on demand. This keeps per-session token cost low.
- **Claude Code uses `@` references.** `CLAUDE.md` includes `@.ai-context/05-current-state.md` and `@.ai-context/README.md`, which Claude Code loads as first-class context entries. Codex and Copilot lack this feature; they rely on the prose rule "first, read 05 and 06". This is the one place the three assistants aren't symmetric — we use the capability where it exists.
- **`06-session-log.md` is NOT `@`-referenced.** It grows. Loading it every session would eat context. It's read on demand when the assistant sees the prose instruction.
- **Rotation convention over infrastructure.** Instead of building log rotation into the init script, we document a "keep 20 recent" rule in the file header. Any assistant can enforce it when appending. Simpler than a cron job, survives repo forks.
- **Domain packs are opt-in and extensible.** Mechanism > specific content. Three example packs prove the pattern without anchoring the skill to any one domain.

## Reference files

- `scripts/init.py` — the init script
- `templates/` — all Markdown templates with `{{PLACEHOLDERS}}`
- `templates/glossary-packs/README.md` — how packs are structured
- `assets/example/todo-api/` — fully rendered example
- `evals/evals.json` — trigger evaluation test cases
