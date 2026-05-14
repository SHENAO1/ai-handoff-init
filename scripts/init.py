#!/usr/bin/env python3
"""ai-handoff-init — bootstrap cross-assistant project context.

Creates a `.ai-context/` directory with 9 Markdown files plus three entry
files (`CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`) that all
point to it. See ../SKILL.md and ../README.md for the rationale.

Runs on Python 3.8+. Standard library only.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ----------------------------------------------------------------------------
# Configuration — edit GLOSSARY_PACKS when adding a new domain pack.
# ----------------------------------------------------------------------------

VERSION = "0.3.0"
CONTEXT_PROTOCOL_VERSION = "0.3.0"

GLOSSARY_PACKS: Dict[str, str] = {
    "web": "web-fullstack.md",
    "ml": "ml-basics.md",
    "gnss-sdr": "gnss-sdr.md",
    "gnss": "gnss-sdr.md",
    "sdr": "gnss-sdr.md",
}

ASSISTANT_DISPLAY: Dict[str, str] = {
    "claude": "Claude Code",
    "codex": "Codex",
    "copilot": "GitHub Copilot",
}

# Paths relative to this script. Resolved once at startup.
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
TEMPLATES_DIR = SKILL_ROOT / "templates"
AI_CONTEXT_TEMPLATES = TEMPLATES_DIR / "ai-context"
ENTRY_TEMPLATES = TEMPLATES_DIR / "entry"
GLOSSARY_PACKS_DIR = TEMPLATES_DIR / "glossary-packs"

AI_CONTEXT_FILES = [
    "README.md",
    "00-overview.md",
    "01-architecture.md",
    "02-conventions.md",
    "03-glossary.md",
    "04-decisions.md",
    "05-current-state.md",
    "06-session-log.md",
    "07-known-issues.md",
]

ENTRY_FILES = [
    # (template filename, destination path relative to target root)
    ("CLAUDE.md.tmpl", "CLAUDE.md"),
    ("AGENTS.md.tmpl", "AGENTS.md"),
    ("copilot-instructions.md.tmpl", ".github/copilot-instructions.md"),
]

GLOSSARY_SLOT = "<!-- DOMAIN_GLOSSARY_SLOT -->"

ENTRY_AUTONOMY_LINE = (
    "在 `.ai-context/02-conventions.md` 的 AI Autonomy Policy 边界内,"
    "优先直接执行用户请求;只有越界、高风险或事实无法从仓库确认时才先问。"
)
ENTRY_COMPLETION_LINE = (
    "完成用户请求后,用简短最终回复汇报 Done / Changed files / Validation / Next or risks。"
)

AUTONOMY_POLICY_BLOCK = """### AI Autonomy Policy

- 默认行动优先:用户要求实现、修复、整理或验证时,在下列边界内直接推进,不要把普通执行变成反复请示。
- 可以直接执行:
  - 阅读、搜索和总结仓库文件。
  - 运行本地测试、lint、format、构建、只读检查和安全的诊断命令。
  - 按现有模式完成小范围 bugfix、功能补充、测试补充、文档更新和模板调整。
  - 更新与本次工作直接相关的 `.ai-context/` 状态、验证记录和交接日志。
- 必须先确认:
  - 删除或迁移大量文件、执行不可逆操作、重写提交历史。
  - 改公开 API、数据模型、持久化格式、认证授权、安全边界或发布流程。
  - 新增生产依赖、外部服务、付费资源、云权限或会影响部署环境的配置。
  - 处理密钥、生产数据、用户隐私数据,或需要联网访问非公开系统。
- 记录规则:
  - 普通代码改动不因行数触发 ADR。
  - 只有架构、依赖、公开接口、数据模型、长期流程约定变化时,才在 `04-decisions.md` 记录原因和影响。
  - 遇到阻塞写进 `07-known-issues.md`,不要悄悄绕过。
  - 不确定的事实先从仓库、测试、文档或 `.ai-context/` 查证;查不到且继续执行会带来明显风险时再询问用户。
"""

COMPLETION_REPORT_BLOCK = """### Completion Report / Definition of Done

- 在 AI Autonomy Policy 边界内的任务应直接完成,不要只给建议或计划。
- 若代码、计划、状态或结论变化,更新 `05-current-state.md`。
- 若发生可交接变化,在 `06-session-log.md` 顶部追加条目。
- 最终回复必须简短说明:Done / Changed files / Validation / Next or risks。
- `06-session-log.md` 是给下一位 AI 的 baton;最终回复是给用户的执行回报,两者不能互相替代。
"""

SESSION_LOG_BATON_NOTE = (
    "> 本文件是给下一位 AI 的 baton;最终回复是给用户的执行回报。"
    "两者字段可以相似,但不能互相替代。\n>"
)

SESSION_LOG_FIELD_LINES = [
    "> **改动文件 / Changed files**: ...",
    "> **验证 / Validation**: ...",
    "> **剩余风险 / Remaining risk**: ...",
]

CURRENT_STATE_SECTIONS = [
    (
        "## 🎯 Current Goal",
        "## 🎯 Current Goal\n- TODO: 明确当前目标\n",
    ),
    (
        "## ⏭️ Next Exact Step",
        "## ⏭️ Next Exact Step\n- TODO: 写下下一位助手应直接执行的下一步\n",
    ),
    (
        "## 🧪 Validation Command",
        "## 🧪 Validation Command\n```bash\n# TODO: 写下下一位助手应优先运行的验证命令\n```\n",
    ),
    (
        "## 🤖 Autonomy Notes",
        "## 🤖 Autonomy Notes\n"
        "- 在 `02-conventions.md` 的 AI Autonomy Policy 边界内,后续助手可以直接推进。\n"
        "- 如果下一步涉及公开 API、数据模型、依赖或不可逆操作,先向用户确认。\n",
    ),
]


# ----------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------


def render(template_text: str, ctx: Dict[str, str]) -> str:
    """Replace `{{KEY}}` placeholders with values from ctx."""
    out = template_text
    for key, val in ctx.items():
        out = out.replace("{{" + key + "}}", val)
    return out


def load_glossary_injection(domain_keywords: List[str]) -> str:
    """Read matching glossary packs and concatenate them.

    Keywords are matched case-insensitively against GLOSSARY_PACKS keys.
    Unmatched keywords are silently ignored. Duplicate packs are deduplicated.
    """
    if not domain_keywords:
        return ""
    seen: List[str] = []
    parts: List[str] = []
    for kw in domain_keywords:
        filename = GLOSSARY_PACKS.get(kw.strip().lower())
        if not filename or filename in seen:
            continue
        pack_path = GLOSSARY_PACKS_DIR / filename
        if not pack_path.exists():
            print(f"warn: glossary pack not found: {pack_path}", file=sys.stderr)
            continue
        parts.append(pack_path.read_text(encoding="utf-8").rstrip())
        seen.append(filename)
    return "\n\n".join(parts)


def inject_glossary(text: str, injection: str) -> str:
    """Replace the glossary slot. If injection is empty, remove the marker."""
    return text.replace(GLOSSARY_SLOT, injection if injection else "")


def render_ai_context_file(name: str, ctx: Dict[str, str], glossary_injection: str) -> str:
    src = (AI_CONTEXT_TEMPLATES / name).read_text(encoding="utf-8")
    if name == "03-glossary.md":
        src = inject_glossary(src, glossary_injection)
    return render(src, ctx)


def render_entry_file(tmpl_name: str, ctx: Dict[str, str]) -> str:
    src = (ENTRY_TEMPLATES / tmpl_name).read_text(encoding="utf-8")
    return render(src, ctx)


# ----------------------------------------------------------------------------
# Planning and writing
# ----------------------------------------------------------------------------


def build_context(args: argparse.Namespace) -> Dict[str, str]:
    stack_items = [s.strip() for s in (args.stack or "").split(",") if s.strip()]
    tech_stack_inline = ", ".join(stack_items) if stack_items else "(待填写)"
    tech_stack_list = "\n".join(f"- {item}" for item in stack_items) if stack_items else "- (待填写)"

    return {
        "PROJECT_NAME": args.name,
        "DESCRIPTION": args.description,
        "TECH_STACK_INLINE": tech_stack_inline,
        "TECH_STACK_LIST": tech_stack_list,
        "INIT_DATE": _dt.date.today().isoformat(),
        "INIT_ASSISTANT": ASSISTANT_DISPLAY[args.assistant],
        "CONTEXT_PROTOCOL_VERSION": CONTEXT_PROTOCOL_VERSION,
    }


def build_plan(target: Path, ctx: Dict[str, str], domain_keywords: List[str]) -> List[Tuple[Path, str]]:
    """Return a list of (dest_path, rendered_content) pairs to write."""
    glossary_injection = load_glossary_injection(domain_keywords)

    plan: List[Tuple[Path, str]] = []

    # .ai-context/ files
    for name in AI_CONTEXT_FILES:
        content = render_ai_context_file(name, ctx, glossary_injection)
        plan.append((target / ".ai-context" / name, content))

    # Entry files
    for tmpl_name, dest_rel in ENTRY_FILES:
        content = render_entry_file(tmpl_name, ctx)
        plan.append((target / dest_rel, content))

    return plan


def detect_conflicts(plan: List[Tuple[Path, str]]) -> Tuple[List[Path], List[Path]]:
    """Split existing destinations into (ai_context_conflicts, entry_conflicts)."""
    ai_ctx_conflicts: List[Path] = []
    entry_conflicts: List[Path] = []
    for dest, _ in plan:
        if dest.exists():
            if ".ai-context" in dest.parts:
                ai_ctx_conflicts.append(dest)
            else:
                entry_conflicts.append(dest)
    return ai_ctx_conflicts, entry_conflicts


def find_existing_ai_context_entries(target: Path) -> List[Path]:
    """Return existing files under .ai-context/, including non-template files."""
    ai_context = target / ".ai-context"
    if not ai_context.exists():
        return []
    if ai_context.is_file():
        return [ai_context]
    return sorted(
        (path for path in ai_context.rglob("*") if path.is_file()),
        key=lambda path: str(path),
    )


def write_plan(plan: List[Tuple[Path, str]], backup_existing: bool) -> List[Path]:
    """Write files to disk. Returns the list of paths actually written."""
    written: List[Path] = []
    timestamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")

    for dest, content in plan:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and backup_existing:
            backup = dest.with_suffix(dest.suffix + f".bak-{timestamp}")
            shutil.copy2(dest, backup)
            print(f"  backup: {dest} -> {backup.name}")
        dest.write_text(content, encoding="utf-8")
        written.append(dest)
    return written


# ----------------------------------------------------------------------------
# Doctor and conservative upgrade
# ----------------------------------------------------------------------------


def _rel(path: str) -> Path:
    return Path(path.replace("/", os.sep))


def _insert_before_marker(text: str, marker: str, block: str) -> str:
    if marker in text:
        return text.replace(marker, block.rstrip() + "\n\n" + marker, 1)
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def _insert_after_line(text: str, anchor: str, line: str) -> str:
    if line in text:
        return text
    lines = text.splitlines()
    for idx, existing in enumerate(lines):
        if existing == anchor:
            lines.insert(idx + 1, line)
            return "\n".join(lines) + "\n"
    return text.rstrip() + "\n" + line + "\n"


def _ensure_protocol_marker(text: str) -> str:
    marker = f"ai-handoff-init protocol: {CONTEXT_PROTOCOL_VERSION}"
    if marker in text:
        return text
    if "ai-handoff-init protocol:" in text:
        return re.sub(r"ai-handoff-init protocol: [^\n]+", marker, text, count=1)
    return _insert_before_marker(text, "\n## 文件导航", marker)


def _ensure_ai_context_readme_rules(text: str) -> str:
    out = _ensure_protocol_marker(text)
    autonomy = (
        "默认行动边界见 `02-conventions.md` 的 AI Autonomy Policy:"
        "在授权边界内优先直接执行,只有越界、高风险或事实无法从仓库确认时才先问。"
    )
    completion = (
        "完成用户请求后,最终回复应简短说明 Done / Changed files / Validation / Next or risks;"
        "这是给用户的执行回报,不替代 `06-session-log.md` 的交接记录。"
    )
    for line in (autonomy, completion):
        if line not in out:
            out = _insert_before_marker(out, "\n## 维护原则", line)
    return out


def _upgrade_entry_text(text: str) -> str:
    if "## 默认工作方式" not in text:
        block = f"## 默认工作方式\n{ENTRY_AUTONOMY_LINE}\n{ENTRY_COMPLETION_LINE}"
        return _insert_before_marker(text, "\n## 会话交接三条铁律", block)

    out = text
    if ENTRY_AUTONOMY_LINE not in out:
        out = _insert_after_line(out, "## 默认工作方式", ENTRY_AUTONOMY_LINE)
    if ENTRY_COMPLETION_LINE not in out:
        if ENTRY_AUTONOMY_LINE in out:
            out = _insert_after_line(out, ENTRY_AUTONOMY_LINE, ENTRY_COMPLETION_LINE)
        else:
            out = _insert_after_line(out, "## 默认工作方式", ENTRY_COMPLETION_LINE)
    return out


def _upgrade_conventions_text(text: str) -> str:
    out = text
    if "## AI 助手协作约定" not in out:
        out = out.rstrip() + "\n\n## AI 助手协作约定\n"
    if "### AI Autonomy Policy" not in out:
        out = out.rstrip() + "\n\n" + AUTONOMY_POLICY_BLOCK.rstrip() + "\n"
    if "### Completion Report / Definition of Done" not in out:
        out = out.rstrip() + "\n\n" + COMPLETION_REPORT_BLOCK.rstrip() + "\n"
    return out


def _upgrade_current_state_text(text: str) -> str:
    out = text
    insert_marker = "\n## ⚠️ Blocked"
    for heading, block in CURRENT_STATE_SECTIONS:
        if heading not in out:
            out = _insert_before_marker(out, insert_marker, block)
    return out


def _upgrade_session_log_text(text: str) -> str:
    out = text
    if "本文件是给下一位 AI 的 baton" not in out:
        out = _insert_before_marker(out, "\n> **条目格式 / Entry format**:", SESSION_LOG_BATON_NOTE)

    missing_lines = [line for line in SESSION_LOG_FIELD_LINES if line not in out]
    if missing_lines:
        block = "\n".join(missing_lines)
        anchor = "> **进行中 / In progress**: ..."
        if anchor in out:
            out = _insert_after_line(out, anchor, block)
        else:
            out = _insert_before_marker(out, "\n> **下一步建议 / Next**: ...", block)
    return out


def _upgrade_text_for_relpath(relpath: str, text: str) -> str:
    if relpath == ".ai-context/README.md":
        return _ensure_ai_context_readme_rules(text)
    if relpath == ".ai-context/02-conventions.md":
        return _upgrade_conventions_text(text)
    if relpath == ".ai-context/05-current-state.md":
        return _upgrade_current_state_text(text)
    if relpath == ".ai-context/06-session-log.md":
        return _upgrade_session_log_text(text)
    if relpath in {dest for _, dest in ENTRY_FILES}:
        return _upgrade_entry_text(text)
    return text


def _upgrade_targets() -> List[str]:
    return [
        ".ai-context/README.md",
        ".ai-context/02-conventions.md",
        ".ai-context/05-current-state.md",
        ".ai-context/06-session-log.md",
        *(dest for _, dest in ENTRY_FILES),
    ]


def run_upgrade(target: Path, dry_run: bool) -> int:
    if not (target / ".ai-context").is_dir():
        print(
            "error: .ai-context/ not found; run normal init before --upgrade.",
            file=sys.stderr,
        )
        return 2

    changes: List[Tuple[Path, str]] = []
    skipped: List[str] = []
    for relpath in _upgrade_targets():
        path = target / _rel(relpath)
        if not path.exists():
            skipped.append(relpath)
            continue
        old = path.read_text(encoding="utf-8")
        new = _upgrade_text_for_relpath(relpath, old)
        if new != old:
            changes.append((path, new))

    prefix = "[upgrade dry-run]" if dry_run else "[upgrade]"
    if not changes:
        print(f"{prefix} up to date: {target}")
    else:
        print(f"{prefix} files to update in: {target}")
        for path, _ in changes:
            print(f"  {path.relative_to(target)}")
        if not dry_run:
            write_plan(changes, backup_existing=True)

    if skipped:
        print("skipped missing files:")
        for relpath in skipped:
            print(f"  {relpath}")
    return 0


def _doctor_checks() -> List[Tuple[str, str, str]]:
    entry_checks: List[Tuple[str, str, str]] = []
    for _, relpath in ENTRY_FILES:
        entry_checks.extend([
            (relpath, "AI Autonomy Policy", "entry autonomy rule"),
            (relpath, "Done / Changed files / Validation / Next or risks", "entry completion report"),
        ])
    return [
        (
            ".ai-context/README.md",
            f"ai-handoff-init protocol: {CONTEXT_PROTOCOL_VERSION}",
            "protocol marker",
        ),
        (".ai-context/02-conventions.md", "AI Autonomy Policy", "AI Autonomy Policy"),
        (
            ".ai-context/02-conventions.md",
            "Completion Report / Definition of Done",
            "Completion Report / Definition of Done",
        ),
        (".ai-context/05-current-state.md", "## 🎯 Current Goal", "current goal field"),
        (".ai-context/05-current-state.md", "## ⏭️ Next Exact Step", "next exact step field"),
        (".ai-context/05-current-state.md", "## 🧪 Validation Command", "validation command field"),
        (".ai-context/05-current-state.md", "## 🤖 Autonomy Notes", "autonomy notes field"),
        (".ai-context/06-session-log.md", "本文件是给下一位 AI 的 baton", "baton note"),
        (".ai-context/06-session-log.md", "**改动文件 / Changed files**", "changed files field"),
        (".ai-context/06-session-log.md", "**验证 / Validation**", "validation field"),
        (".ai-context/06-session-log.md", "**剩余风险 / Remaining risk**", "remaining risk field"),
        *entry_checks,
    ]


def run_doctor(target: Path) -> int:
    ok: List[str] = []
    missing: List[str] = []
    outdated: List[str] = []

    if (target / ".ai-context").is_dir():
        ok.append(".ai-context/")
    else:
        missing.append(".ai-context/")

    required = [f".ai-context/{name}" for name in AI_CONTEXT_FILES]
    required.extend(dest for _, dest in ENTRY_FILES)
    for relpath in required:
        path = target / _rel(relpath)
        if path.exists():
            ok.append(relpath)
        else:
            missing.append(relpath)

    for relpath, fragment, label in _doctor_checks():
        path = target / _rel(relpath)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if fragment in text:
            ok.append(f"{relpath}: {label}")
        else:
            outdated.append(f"{relpath}: missing {label}")

    print(f"Doctor target: {target}")
    for heading, items in (("OK", ok), ("MISSING", missing), ("OUTDATED", outdated)):
        print(f"{heading}:")
        if items:
            for item in items:
                print(f"  - {item}")
        else:
            print("  - (none)")

    return 0 if not missing and not outdated else 1


# ----------------------------------------------------------------------------
# Entry-file snippet printer
# ----------------------------------------------------------------------------


def print_entry_snippets(ctx: Dict[str, str], heading: str = "ENTRY SNIPPETS") -> None:
    """Print what the user should paste into their existing entry files."""
    print()
    print("=" * 72)
    print(f"{heading} — paste these snippets into your existing entry files")
    print("=" * 72)

    for tmpl_name, dest_rel in ENTRY_FILES:
        content = render_entry_file(tmpl_name, ctx)
        print(f"\n--- {dest_rel} ---")
        print(content.rstrip())
    print()
    print("=" * 72)


# ----------------------------------------------------------------------------
# Interactive prompts
# ----------------------------------------------------------------------------


def _prompt(label: str, default: Optional[str] = None, required: bool = True) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        try:
            raw = input(f"{label}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\naborted.", file=sys.stderr)
            sys.exit(130)
        if raw:
            return raw
        if default is not None:
            return default
        if not required:
            return ""
        print("  (required)")


def _prompt_choice(label: str, choices: List[str], default: Optional[str] = None) -> str:
    label_with_choices = f"{label} ({'/'.join(choices)})"
    while True:
        ans = _prompt(label_with_choices, default=default)
        if ans in choices:
            return ans
        print(f"  must be one of: {', '.join(choices)}")


def interactive_fill(args: argparse.Namespace) -> argparse.Namespace:
    """Prompt for any missing required fields."""
    if not args.name:
        args.name = _prompt("Project name")
    if not args.description:
        args.description = _prompt("One-sentence description")
    if args.stack is None:
        args.stack = _prompt("Tech stack (comma-separated)", required=False)
    if not args.stage:
        args.stage = _prompt_choice("Project stage", ["new", "existing"], default="new")
    if args.domains is None:
        args.domains = _prompt(
            "Domain keywords (optional, comma-separated; built-in: web, ml, gnss-sdr)",
            required=False,
        )
    if not args.assistant:
        args.assistant = _prompt_choice(
            "Which assistant is running init", ["claude", "codex", "copilot"], default="claude"
        )
    return args


# ----------------------------------------------------------------------------
# Output helpers
# ----------------------------------------------------------------------------


def print_tree(target: Path, plan: List[Tuple[Path, str]]) -> None:
    rels = sorted(str(dest.relative_to(target)) for dest, _ in plan)
    print(f"\n  {target}")
    for r in rels:
        print(f"    {r}")


def print_available_packs() -> None:
    """Print the glossary packs that --domains knows about, grouped by file."""
    # Invert the map: filename -> sorted list of keyword aliases.
    by_file: Dict[str, List[str]] = {}
    for kw, fname in GLOSSARY_PACKS.items():
        by_file.setdefault(fname, []).append(kw)

    print("Available glossary packs (use with --domains):\n")
    # Sort by filename for stable output; sort aliases within each group too.
    rows = sorted((sorted(kws), fname) for fname, kws in by_file.items())
    key_col_width = max(len(", ".join(kws)) for kws, _ in rows)
    for kws, fname in rows:
        keys = ", ".join(kws)
        print(f"  {keys:<{key_col_width}}  ->  {fname}")


def print_next_steps(ctx: Dict[str, str], stage: str) -> None:
    print("\nNext steps:")
    print("  1. Read the three handoff rules in .ai-context/README.md")
    if stage == "existing":
        print("  2. Ask your current assistant to scan the repo and prefill")
        print("     .ai-context/00-overview.md (goals) and 01-architecture.md (modules)")
    else:
        print("  2. Fill .ai-context/00-overview.md with project goals")
        print("     and 01-architecture.md with the module layout as you design it")
    print("  3. Start real work. End every session by updating 05 + prepending to 06.")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="init.py",
        description="Bootstrap cross-assistant project context.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python init.py                              # interactive mode
  python init.py --name todo-api --description "Todo REST API" \\
                 --stack "Python,FastAPI,PostgreSQL" --stage new --as claude

  python init.py --merge --name todo-api ...  # only create .ai-context/,
                                              # print entry-file snippets

  python init.py --print-snippets --name todo-api ...
                                              # print entry-file snippets only

  python init.py --doctor --target /path/to/project
                                              # check an existing context

  python init.py --upgrade --target /path/to/project --dry-run
                                              # preview conservative upgrade
""",
    )
    p.add_argument("--target", type=Path, default=Path.cwd(),
                   help="project root to initialize (default: current dir)")
    p.add_argument("--name", help="project name (short slug)")
    p.add_argument("--description", help="one-sentence description")
    p.add_argument("--stack", help='comma-separated tech stack, e.g. "Python,FastAPI"')
    p.add_argument("--stage", choices=["new", "existing"],
                   help="whether this is a fresh repo or has code already")
    p.add_argument("--domains",
                   help="comma-separated glossary pack keywords (optional); "
                        "built-in: web, ml, gnss-sdr")
    p.add_argument("--as", dest="assistant", choices=["claude", "codex", "copilot"],
                   help="which assistant is running init")
    p.add_argument("--force", action="store_true",
                   help="overwrite existing entry files (auto-backup as .bak-*). "
                        "Will NOT overwrite existing .ai-context/")
    p.add_argument("--merge", action="store_true",
                   help="only create .ai-context/; print entry-file snippets for "
                        "manual paste into your existing CLAUDE.md/AGENTS.md/etc.")
    p.add_argument("--print-snippets", action="store_true",
                   help="print rendered CLAUDE.md, AGENTS.md, and Copilot "
                        "instruction snippets only; write no files")
    p.add_argument("--dry-run", action="store_true",
                   help="print the plan without writing any files")
    p.add_argument("--doctor", action="store_true",
                   help="check an existing .ai-context/ protocol without writing files")
    p.add_argument("--upgrade", action="store_true",
                   help="conservatively upgrade an existing .ai-context/ protocol")
    p.add_argument("--list-packs", action="store_true",
                   help="list available glossary packs and exit")
    p.add_argument("--version", action="version", version=f"ai-handoff-init {VERSION}")
    return p


SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def validate_args(args: argparse.Namespace) -> None:
    # stage/assistant/description are already guaranteed non-empty by the
    # combination of argparse choices + interactive_fill(). Only check the
    # constraints neither of them covers: mutex flags and slug format.
    if args.force and args.merge:
        sys.exit("error: --force and --merge are mutually exclusive")
    if args.print_snippets and (args.force or args.merge or args.dry_run):
        sys.exit("error: --print-snippets cannot be combined with --force, --merge, or --dry-run")
    if not SLUG_RE.match(args.name or ""):
        sys.exit(f"error: project name must match {SLUG_RE.pattern}; got {args.name!r}")


def validate_maintenance_args(args: argparse.Namespace) -> None:
    if args.doctor and args.upgrade:
        sys.exit("error: --doctor and --upgrade are mutually exclusive")
    if not (args.doctor or args.upgrade):
        return

    common_invalid = [
        (args.name, "--name"),
        (args.description, "--description"),
        (args.stack, "--stack"),
        (args.stage, "--stage"),
        (args.domains, "--domains"),
        (args.assistant, "--as"),
        (args.force, "--force"),
        (args.merge, "--merge"),
        (args.print_snippets, "--print-snippets"),
    ]
    invalid = [flag for value, flag in common_invalid if value]
    if args.doctor and args.dry_run:
        invalid.append("--dry-run")
    if invalid:
        mode = "--doctor" if args.doctor else "--upgrade"
        allowed = "--target" if args.doctor else "--target and optional --dry-run"
        sys.exit(f"error: {mode} can only be combined with {allowed}; got {', '.join(invalid)}")


def parse_domain_keywords(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [kw.strip() for kw in raw.split(",") if kw.strip()]


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # Informational flags short-circuit before any validation so users can
    # always `--list-packs` regardless of target / project state.
    if args.list_packs:
        print_available_packs()
        return 0

    validate_maintenance_args(args)

    # Validate target early — before prompting the user for anything else.
    # A broken --target is cheap to detect and annoying to hit after five
    # interactive prompts.
    target: Path = args.target.resolve()
    if not target.exists():
        sys.exit(f"error: target does not exist: {target}")
    if not target.is_dir():
        sys.exit(f"error: target is not a directory: {target}")

    if args.doctor:
        return run_doctor(target)
    if args.upgrade:
        return run_upgrade(target, dry_run=args.dry_run)

    # Interactive fallback for any missing required field.
    missing_required = not (args.name and args.description and args.stage and args.assistant)
    if missing_required:
        args = interactive_fill(args)

    validate_args(args)

    ctx = build_context(args)
    domain_keywords = parse_domain_keywords(args.domains)

    if args.print_snippets:
        print_entry_snippets(ctx)
        return 0

    # Per-keyword unknowns stay silent (documented design). But if the user
    # typed some keywords and NONE of them matched, they probably mistyped —
    # surface one heads-up. Use --list-packs to see valid keys.
    if domain_keywords and not any(
        kw.strip().lower() in GLOSSARY_PACKS for kw in domain_keywords
    ):
        print(
            "info: none of --domains keywords matched a built-in pack; "
            "no glossary will be injected. Run with --list-packs to see options.",
            file=sys.stderr,
        )

    plan = build_plan(target, ctx, domain_keywords)

    # Conflict detection
    ai_ctx_conflicts, entry_conflicts = detect_conflicts(plan)
    seen_ai_ctx_conflicts = set(ai_ctx_conflicts)
    for path in find_existing_ai_context_entries(target):
        if path not in seen_ai_ctx_conflicts:
            ai_ctx_conflicts.append(path)
            seen_ai_ctx_conflicts.add(path)

    if args.merge:
        # Merge mode: only write .ai-context/, refuse if that exists.
        if ai_ctx_conflicts:
            print("error: .ai-context/ already has files; --merge cannot proceed:",
                  file=sys.stderr)
            for c in ai_ctx_conflicts:
                print(f"  {c}", file=sys.stderr)
            print("       keep the existing .ai-context/ and re-run with --print-snippets",
                  file=sys.stderr)
            print("       to print entry-file snippets without writing files.",
                  file=sys.stderr)
            return 2
        # Filter plan to only .ai-context/ files.
        plan = [(d, c) for (d, c) in plan if ".ai-context" in d.parts]
    else:
        # Normal / force mode
        if ai_ctx_conflicts:
            print("error: .ai-context/ already contains files; refusing to overwrite.",
                  file=sys.stderr)
            print("       move or delete the existing .ai-context/ to re-init,",
                  file=sys.stderr)
            print("       or re-run with --print-snippets to keep it and only print",
                  file=sys.stderr)
            print("       entry-file snippets without writing files.",
                  file=sys.stderr)
            for c in ai_ctx_conflicts:
                print(f"  {c}", file=sys.stderr)
            return 2
        if entry_conflicts and not args.force:
            print("error: entry files already exist:", file=sys.stderr)
            for c in entry_conflicts:
                print(f"  {c}", file=sys.stderr)
            print("       re-run with --force to overwrite (backups will be created),",
                  file=sys.stderr)
            print("       or with --merge to leave them alone and only print snippets.",
                  file=sys.stderr)
            return 2

    # Dry-run
    if args.dry_run:
        print(f"[dry-run] would create / overwrite in: {target}")
        print_tree(target, plan)
        total = sum(len(c.encode("utf-8")) for _, c in plan)
        print(f"\n  total: {len(plan)} files, {total:,} bytes")
        if args.merge:
            print_entry_snippets(ctx, heading="MERGE MODE")
        return 0

    # Write
    written = write_plan(plan, backup_existing=args.force)
    print(f"wrote {len(written)} files to {target}")
    print_tree(target, plan)

    if args.merge:
        print_entry_snippets(ctx, heading="MERGE MODE")
    else:
        print_next_steps(ctx, args.stage)

    return 0


if __name__ == "__main__":
    sys.exit(main())
