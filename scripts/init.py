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


def detect_conflicts(plan: List[Tuple[Path, str]], mode: str) -> Tuple[List[Path], List[Path]]:
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
# Merge-mode snippet printer
# ----------------------------------------------------------------------------


def print_merge_snippets(ctx: Dict[str, str]) -> None:
    """Print what the user should paste into their existing entry files."""
    print()
    print("=" * 72)
    print("MERGE MODE — paste these snippets into your existing entry files")
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
    p.add_argument("--dry-run", action="store_true",
                   help="print the plan without writing any files")
    p.add_argument("--version", action="version", version="ai-handoff-init 0.1.0")
    return p


SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def validate_args(args: argparse.Namespace) -> None:
    if args.force and args.merge:
        sys.exit("error: --force and --merge are mutually exclusive")
    if not SLUG_RE.match(args.name or ""):
        sys.exit(f"error: project name must match {SLUG_RE.pattern}; got {args.name!r}")
    if not args.description:
        sys.exit("error: --description is required")
    if args.stage not in ("new", "existing"):
        sys.exit("error: --stage must be 'new' or 'existing'")
    if args.assistant not in ASSISTANT_DISPLAY:
        sys.exit("error: --as must be one of claude, codex, copilot")


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

    # Interactive fallback for any missing required field.
    missing_required = not (args.name and args.description and args.stage and args.assistant)
    if missing_required:
        args = interactive_fill(args)

    validate_args(args)

    target: Path = args.target.resolve()
    if not target.exists():
        sys.exit(f"error: target does not exist: {target}")
    if not target.is_dir():
        sys.exit(f"error: target is not a directory: {target}")

    ctx = build_context(args)
    domain_keywords = parse_domain_keywords(args.domains)
    plan = build_plan(target, ctx, domain_keywords)

    # Conflict detection
    ai_ctx_conflicts, entry_conflicts = detect_conflicts(plan, mode="normal")

    if args.merge:
        # Merge mode: only write .ai-context/, refuse if that exists.
        if ai_ctx_conflicts:
            print("error: .ai-context/ already has files; --merge cannot proceed:",
                  file=sys.stderr)
            for c in ai_ctx_conflicts:
                print(f"  {c}", file=sys.stderr)
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
            print("       or re-run with --merge to keep it and only print entry snippets.",
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
            print_merge_snippets(ctx)
        return 0

    # Write
    written = write_plan(plan, backup_existing=args.force)
    print(f"✓ wrote {len(written)} files to {target}")
    print_tree(target, plan)

    if args.merge:
        print_merge_snippets(ctx)
    else:
        print_next_steps(ctx, args.stage)

    return 0


if __name__ == "__main__":
    sys.exit(main())
