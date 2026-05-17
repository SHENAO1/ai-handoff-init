"""Tests for scripts/init.py.

Uses stdlib unittest to stay consistent with the script's stdlib-only policy.
Run with: python -m unittest discover -s tests
"""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Make scripts/init.py importable without installing.
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT / "scripts"))

import init  # noqa: E402


EXPECTED_VERSION = "0.3.0"


# ----------------------------------------------------------------------------
# Version consistency tests
# ----------------------------------------------------------------------------


class TestVersionConsistency(unittest.TestCase):
    def test_cli_version_output(self):
        result = subprocess.run(
            [sys.executable, str(_ROOT / "scripts" / "init.py"), "--version"],
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), f"ai-handoff-init {EXPECTED_VERSION}")

    def test_skill_frontmatter_version(self):
        lines = (_ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()
        self.assertGreaterEqual(len(lines), 4)
        self.assertEqual(lines[0], "---")
        end = lines.index("---", 1)
        frontmatter = lines[1:end]
        self.assertIn(f"version: {EXPECTED_VERSION}", frontmatter)


# ----------------------------------------------------------------------------
# Pure function tests
# ----------------------------------------------------------------------------


class TestRender(unittest.TestCase):
    def test_replaces_single_placeholder(self):
        self.assertEqual(
            init.render("Hi {{NAME}}!", {"NAME": "todo-api"}),
            "Hi todo-api!",
        )

    def test_replaces_multiple_placeholders(self):
        result = init.render(
            "{{A}} / {{B}} / {{A}}",
            {"A": "x", "B": "y"},
        )
        self.assertEqual(result, "x / y / x")

    def test_unknown_placeholder_preserved(self):
        self.assertEqual(
            init.render("Hi {{UNKNOWN}}", {"NAME": "v"}),
            "Hi {{UNKNOWN}}",
        )

    def test_empty_context_is_noop(self):
        self.assertEqual(init.render("plain text", {}), "plain text")


class TestParseDomainKeywords(unittest.TestCase):
    def test_none_returns_empty(self):
        self.assertEqual(init.parse_domain_keywords(None), [])

    def test_empty_string_returns_empty(self):
        self.assertEqual(init.parse_domain_keywords(""), [])

    def test_comma_separated(self):
        self.assertEqual(
            init.parse_domain_keywords("web, ml, gnss-sdr"),
            ["web", "ml", "gnss-sdr"],
        )

    def test_filters_empty_fragments(self):
        self.assertEqual(
            init.parse_domain_keywords("web,,ml, "),
            ["web", "ml"],
        )


class TestLoadGlossaryInjection(unittest.TestCase):
    def test_no_keywords_returns_empty(self):
        self.assertEqual(init.load_glossary_injection([]), "")

    def test_matches_web_pack(self):
        out = init.load_glossary_injection(["web"])
        self.assertIn("REST", out)
        self.assertNotEqual(out, "")

    def test_case_insensitive(self):
        self.assertEqual(
            init.load_glossary_injection(["WEB"]),
            init.load_glossary_injection(["web"]),
        )

    def test_unknown_keyword_silently_ignored(self):
        # Documented behavior: unknown packs do not error.
        self.assertEqual(
            init.load_glossary_injection(["nonexistent-pack"]),
            "",
        )

    def test_deduplicates_aliased_packs(self):
        # gnss, sdr, gnss-sdr all map to the same file.
        once = init.load_glossary_injection(["gnss-sdr"])
        thrice = init.load_glossary_injection(["gnss", "sdr", "gnss-sdr"])
        self.assertEqual(once, thrice)

    def test_concatenates_distinct_packs(self):
        web = init.load_glossary_injection(["web"])
        ml = init.load_glossary_injection(["ml"])
        both = init.load_glossary_injection(["web", "ml"])
        self.assertIn(web, both)
        self.assertIn(ml, both)


class TestInjectGlossary(unittest.TestCase):
    def test_replaces_slot_with_content(self):
        text = f"before\n{init.GLOSSARY_SLOT}\nafter"
        self.assertEqual(
            init.inject_glossary(text, "INJECTED"),
            "before\nINJECTED\nafter",
        )

    def test_empty_injection_removes_marker(self):
        text = f"before\n{init.GLOSSARY_SLOT}\nafter"
        self.assertEqual(
            init.inject_glossary(text, ""),
            "before\n\nafter",
        )


class TestBuildContext(unittest.TestCase):
    def _args(self, **overrides):
        ns = argparse.Namespace(
            name="todo-api",
            description="A todo API",
            stack="Python,FastAPI",
            stage="new",
            domains=None,
            assistant="claude",
        )
        for k, v in overrides.items():
            setattr(ns, k, v)
        return ns

    def test_stack_rendered_inline_and_as_list(self):
        ctx = init.build_context(self._args())
        self.assertEqual(ctx["TECH_STACK_INLINE"], "Python, FastAPI")
        self.assertEqual(ctx["TECH_STACK_LIST"], "- Python\n- FastAPI")

    def test_empty_stack_uses_placeholder(self):
        ctx = init.build_context(self._args(stack=""))
        self.assertIn("待填写", ctx["TECH_STACK_INLINE"])
        self.assertIn("待填写", ctx["TECH_STACK_LIST"])

    def test_assistant_display_name_mapped(self):
        self.assertEqual(
            init.build_context(self._args(assistant="codex"))["INIT_ASSISTANT"],
            "Codex",
        )
        self.assertEqual(
            init.build_context(self._args(assistant="copilot"))["INIT_ASSISTANT"],
            "GitHub Copilot",
        )

    def test_project_name_and_description_passed_through(self):
        ctx = init.build_context(self._args(name="x", description="desc"))
        self.assertEqual(ctx["PROJECT_NAME"], "x")
        self.assertEqual(ctx["DESCRIPTION"], "desc")

    def test_protocol_version_passed_through(self):
        ctx = init.build_context(self._args())
        self.assertEqual(ctx["CONTEXT_PROTOCOL_VERSION"], init.CONTEXT_PROTOCOL_VERSION)


class TestDetectConflicts(unittest.TestCase):
    def test_no_conflicts_on_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            plan = [
                (target / ".ai-context" / "00-overview.md", "x"),
                (target / "CLAUDE.md", "y"),
            ]
            ai, entry = init.detect_conflicts(plan)
            self.assertEqual(ai, [])
            self.assertEqual(entry, [])

    def test_separates_ai_context_and_entry_conflicts(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / ".ai-context").mkdir()
            (target / ".ai-context" / "00-overview.md").write_text("x")
            (target / "CLAUDE.md").write_text("y")
            plan = [
                (target / ".ai-context" / "00-overview.md", "x"),
                (target / "CLAUDE.md", "y"),
                (target / "AGENTS.md", "z"),  # does not exist — no conflict
            ]
            ai, entry = init.detect_conflicts(plan)
            self.assertEqual(len(ai), 1)
            self.assertEqual(len(entry), 1)
            self.assertIn(target / ".ai-context" / "00-overview.md", ai)
            self.assertIn(target / "CLAUDE.md", entry)


class TestBuildPlan(unittest.TestCase):
    def _ctx(self):
        return {
            "PROJECT_NAME": "todo-api",
            "DESCRIPTION": "A todo API",
            "TECH_STACK_INLINE": "Python",
            "TECH_STACK_LIST": "- Python",
            "INIT_DATE": "2026-04-17",
            "INIT_ASSISTANT": "Claude Code",
            "CONTEXT_PROTOCOL_VERSION": init.CONTEXT_PROTOCOL_VERSION,
        }

    def test_plan_includes_all_ai_context_files(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            plan = init.build_plan(target, self._ctx(), [])
            dest_names = {p.name for p, _ in plan if ".ai-context" in p.parts}
            self.assertEqual(dest_names, set(init.AI_CONTEXT_FILES))

    def test_plan_includes_all_entry_files(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            plan = init.build_plan(target, self._ctx(), [])
            entry_paths = {
                str(p.relative_to(target)).replace("\\", "/")
                for p, _ in plan
                if ".ai-context" not in p.parts
            }
            self.assertEqual(
                entry_paths,
                {"CLAUDE.md", "AGENTS.md", ".github/copilot-instructions.md"},
            )

    def test_plan_substitutes_placeholders(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            plan = init.build_plan(target, self._ctx(), [])
            for dest, content in plan:
                self.assertNotIn("{{PROJECT_NAME}}", content, dest.name)
                self.assertNotIn("{{DESCRIPTION}}", content, dest.name)

    def test_plan_injects_glossary_when_domain_matched(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            plan = init.build_plan(target, self._ctx(), ["web"])
            glossary = next(c for p, c in plan if p.name == "03-glossary.md")
            self.assertIn("REST", glossary)
            self.assertNotIn(init.GLOSSARY_SLOT, glossary)

    def test_plan_removes_slot_when_no_domain(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            plan = init.build_plan(target, self._ctx(), [])
            glossary = next(c for p, c in plan if p.name == "03-glossary.md")
            self.assertNotIn(init.GLOSSARY_SLOT, glossary)


class TestGeneratedTemplateContracts(unittest.TestCase):
    """Snapshot-style checks for the generated handoff protocol surface."""

    def _plan_by_relpath(self, target: Path):
        ctx = {
            "PROJECT_NAME": "todo-api",
            "DESCRIPTION": "A todo API",
            "TECH_STACK_INLINE": "Python",
            "TECH_STACK_LIST": "- Python",
            "INIT_DATE": "2026-04-17",
            "INIT_ASSISTANT": "Claude Code",
            "CONTEXT_PROTOCOL_VERSION": init.CONTEXT_PROTOCOL_VERSION,
        }
        return {
            str(path.relative_to(target)).replace("\\", "/"): content
            for path, content in init.build_plan(target, ctx, [])
        }

    def test_entry_files_include_autonomy_boundary_and_stay_short(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            by_path = self._plan_by_relpath(target)
            for relpath in (
                "CLAUDE.md",
                "AGENTS.md",
                ".github/copilot-instructions.md",
            ):
                content = by_path[relpath]
                self.assertIn("AI Autonomy Policy", content, relpath)
                self.assertIn("优先直接执行用户请求", content, relpath)
                self.assertIn("Done / Changed files / Validation / Next or risks", content, relpath)
                self.assertLessEqual(len(content.splitlines()), 20, relpath)

    def test_conventions_define_autonomy_policy_contract(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            content = self._plan_by_relpath(target)[".ai-context/02-conventions.md"]
            expected_fragments = (
                "### AI Autonomy Policy",
                "默认行动优先",
                "可以直接执行",
                "必须先确认",
                "普通代码改动不因行数触发 ADR",
                "架构、依赖、公开接口、数据模型、长期流程约定变化",
                "### Completion Report / Definition of Done",
                "最终回复必须简短说明:Done / Changed files / Validation / Next or risks",
                "两者不能互相替代",
            )
            for fragment in expected_fragments:
                self.assertIn(fragment, content)

    def test_current_state_contains_actionable_handoff_fields(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            content = self._plan_by_relpath(target)[".ai-context/05-current-state.md"]
            for heading in (
                "## 🎯 Current Goal",
                "## ⏭️ Next Exact Step",
                "## 🧪 Validation Command",
                "## 🤖 Autonomy Notes",
            ):
                self.assertIn(heading, content)

    def test_context_readme_contains_protocol_marker(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            content = self._plan_by_relpath(target)[".ai-context/README.md"]
            self.assertIn("ai-handoff-init protocol: 0.3.0", content)

    def test_session_log_contains_validation_and_risk_fields(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            content = self._plan_by_relpath(target)[".ai-context/06-session-log.md"]
            for label in (
                "**改动文件 / Changed files**",
                "**验证 / Validation**",
                "**剩余风险 / Remaining risk**",
                "本文件是给下一位 AI 的 baton",
                "最终回复是给用户的执行回报",
            ):
                self.assertIn(label, content)


# ----------------------------------------------------------------------------
# main() flow branch tests
# ----------------------------------------------------------------------------


def _base_argv(target: Path, extra=()):
    return [
        "--target", str(target),
        "--name", "todo-api",
        "--description", "A todo API",
        "--stack", "Python,FastAPI",
        "--stage", "new",
        "--as", "claude",
        *extra,
    ]


class TestMainDryRun(unittest.TestCase):
    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stdout(io.StringIO()):
                rc = init.main(_base_argv(target, ["--dry-run"]))
            self.assertEqual(rc, 0)
            self.assertFalse((target / ".ai-context").exists())
            self.assertFalse((target / "CLAUDE.md").exists())

    def test_dry_run_prints_plan(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            buf = io.StringIO()
            with redirect_stdout(buf):
                init.main(_base_argv(target, ["--dry-run"]))
            out = buf.getvalue()
            self.assertIn("dry-run", out)
            self.assertIn("CLAUDE.md", out)
            self.assertIn("05-current-state.md", out)


class TestMainNormalWrite(unittest.TestCase):
    def test_writes_all_expected_files(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stdout(io.StringIO()):
                rc = init.main(_base_argv(target))
            self.assertEqual(rc, 0)
            for name in init.AI_CONTEXT_FILES:
                self.assertTrue(
                    (target / ".ai-context" / name).exists(),
                    f"missing: {name}",
                )
            self.assertTrue((target / "CLAUDE.md").exists())
            self.assertTrue((target / "AGENTS.md").exists())
            self.assertTrue((target / ".github" / "copilot-instructions.md").exists())

    def test_placeholders_are_substituted(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stdout(io.StringIO()):
                init.main(_base_argv(target))
            claude = (target / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("todo-api", claude)
            self.assertIn("A todo API", claude)
            self.assertNotIn("{{", claude)

    def test_refuses_when_ai_context_already_has_files(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / ".ai-context").mkdir()
            (target / ".ai-context" / "00-overview.md").write_text("old")
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = init.main(_base_argv(target))
            self.assertEqual(rc, 2)
            message = err.getvalue()
            self.assertIn(".ai-context", message)
            self.assertIn("--print-snippets", message)
            self.assertNotIn("re-run with --merge", message)
            # Pre-existing file must be untouched.
            self.assertEqual(
                (target / ".ai-context" / "00-overview.md").read_text(encoding="utf-8"),
                "old",
            )

    def test_refuses_when_ai_context_has_non_template_file(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / ".ai-context").mkdir()
            (target / ".ai-context" / "custom.md").write_text(
                "existing custom context",
                encoding="utf-8",
            )
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = init.main(_base_argv(target))
            self.assertEqual(rc, 2)
            message = err.getvalue()
            self.assertIn("custom.md", message)
            self.assertIn("--print-snippets", message)
            self.assertFalse((target / ".ai-context" / "00-overview.md").exists())

    def test_refuses_when_entry_file_exists_without_force(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / "CLAUDE.md").write_text("existing")
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = init.main(_base_argv(target))
            self.assertEqual(rc, 2)
            self.assertIn("CLAUDE.md", err.getvalue())
            # Entry file must be untouched.
            self.assertEqual(
                (target / "CLAUDE.md").read_text(encoding="utf-8"),
                "existing",
            )

    def test_force_overwrites_entry_and_backs_up(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / "CLAUDE.md").write_text("old claude content")
            with redirect_stdout(io.StringIO()):
                rc = init.main(_base_argv(target, ["--force"]))
            self.assertEqual(rc, 0)
            new_content = (target / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("todo-api", new_content)
            self.assertNotIn("old claude content", new_content)
            backups = list(target.glob("CLAUDE.md.bak-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(
                backups[0].read_text(encoding="utf-8"),
                "old claude content",
            )


class TestMainMerge(unittest.TestCase):
    def test_merge_creates_ai_context_only(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stdout(io.StringIO()):
                rc = init.main(_base_argv(target, ["--merge"]))
            self.assertEqual(rc, 0)
            self.assertTrue((target / ".ai-context" / "00-overview.md").exists())
            self.assertFalse((target / "CLAUDE.md").exists())
            self.assertFalse((target / "AGENTS.md").exists())
            self.assertFalse((target / ".github" / "copilot-instructions.md").exists())

    def test_merge_prints_snippets(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            buf = io.StringIO()
            with redirect_stdout(buf):
                init.main(_base_argv(target, ["--merge"]))
            out = buf.getvalue()
            self.assertIn("MERGE MODE", out)
            self.assertIn("CLAUDE.md", out)
            self.assertIn("AGENTS.md", out)
            self.assertIn(".github/copilot-instructions.md", out)

    def test_merge_refuses_when_ai_context_has_files(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / ".ai-context").mkdir()
            (target / ".ai-context" / "00-overview.md").write_text("x")
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = init.main(_base_argv(target, ["--merge"]))
            self.assertEqual(rc, 2)
            message = err.getvalue()
            self.assertIn(".ai-context", message)
            self.assertIn("--print-snippets", message)


class TestMainAdopt(unittest.TestCase):
    def test_adopt_imports_existing_entries_moves_backups_and_replaces_entries(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / "CLAUDE.md").write_text("legacy claude rule", encoding="utf-8")
            (target / "AGENTS.md").write_text("legacy agents rule", encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                rc = init.main(_base_argv(target, ["--adopt"]))

            self.assertEqual(rc, 0)

            adopted = (target / ".ai-context" / "09-adopted-instructions.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("legacy claude rule", adopted)
            self.assertIn("legacy agents rule", adopted)
            self.assertIn("Conflict Priority", adopted)

            claude = (target / "CLAUDE.md").read_text(encoding="utf-8")
            agents = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("todo-api", claude)
            self.assertIn("你是 **Codex**", agents)
            self.assertNotIn("legacy claude rule", claude)
            self.assertNotIn("legacy agents rule", agents)

            backup_root = target / ".ai-context" / "adopted-entry-backups"
            claude_backups = list(backup_root.glob("*/CLAUDE.md"))
            agents_backups = list(backup_root.glob("*/AGENTS.md"))
            self.assertEqual(len(claude_backups), 1)
            self.assertEqual(len(agents_backups), 1)
            self.assertEqual(claude_backups[0].read_text(encoding="utf-8"), "legacy claude rule")
            self.assertEqual(agents_backups[0].read_text(encoding="utf-8"), "legacy agents rule")
            manifest = next(backup_root.glob("*/MANIFEST.md")).read_text(encoding="utf-8")
            self.assertIn("CLAUDE.md", manifest)
            self.assertIn("AGENTS.md", manifest)

            readme = (target / ".ai-context" / "README.md").read_text(encoding="utf-8")
            current = (target / ".ai-context" / "05-current-state.md").read_text(
                encoding="utf-8"
            )
            session = (target / ".ai-context" / "06-session-log.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("09-adopted-instructions.md", readme)
            self.assertIn("已收编已有 AI 助手入口文件", current)
            self.assertIn("09-adopted-instructions.md", session)
            self.assertIn("adopted-entry-backups", session)

    def test_adopt_supports_singular_agent_file(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / "AGENT.md").write_text("legacy singular agent rule", encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                rc = init.main(_base_argv(target, ["--adopt"]))

            self.assertEqual(rc, 0)
            self.assertFalse((target / "AGENT.md").exists())
            self.assertTrue((target / "AGENTS.md").exists())
            adopted = (target / ".ai-context" / "09-adopted-instructions.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("AGENT.md", adopted)
            self.assertIn("legacy singular agent rule", adopted)
            backups = list((target / ".ai-context" / "adopted-entry-backups").glob("*/AGENT.md"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "legacy singular agent rule")

    def test_adopt_dry_run_does_not_write_or_move(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / "CLAUDE.md").write_text("legacy claude rule", encoding="utf-8")

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = init.main(_base_argv(target, ["--adopt", "--dry-run"]))

            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn("[adopt dry-run]", out)
            self.assertIn("adopted entry moves", out)
            self.assertIn("09-adopted-instructions.md", out)
            self.assertEqual(
                (target / "CLAUDE.md").read_text(encoding="utf-8"),
                "legacy claude rule",
            )
            self.assertFalse((target / ".ai-context").exists())

    def test_adopt_refuses_when_ai_context_has_files(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / "CLAUDE.md").write_text("legacy claude rule", encoding="utf-8")
            (target / ".ai-context").mkdir()
            (target / ".ai-context" / "custom.md").write_text("existing", encoding="utf-8")

            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = init.main(_base_argv(target, ["--adopt"]))

            self.assertEqual(rc, 2)
            self.assertIn("--adopt cannot proceed", err.getvalue())
            self.assertEqual(
                (target / "CLAUDE.md").read_text(encoding="utf-8"),
                "legacy claude rule",
            )
            self.assertFalse((target / ".ai-context" / "adopted-entry-backups").exists())

    def test_adopt_without_existing_entries_falls_back_to_normal_init(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = init.main(_base_argv(target, ["--adopt"]))

            self.assertEqual(rc, 0)
            self.assertIn("found no existing AI entry files", err.getvalue())
            self.assertTrue((target / ".ai-context" / "00-overview.md").exists())
            self.assertTrue((target / "CLAUDE.md").exists())
            self.assertFalse((target / ".ai-context" / "09-adopted-instructions.md").exists())


class TestMainPrintSnippets(unittest.TestCase):
    def test_print_snippets_prints_entries_without_writing_files(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = init.main(_base_argv(target, ["--print-snippets"]))
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn("ENTRY SNIPPETS", out)
            self.assertIn("CLAUDE.md", out)
            self.assertIn("AGENTS.md", out)
            self.assertIn(".github/copilot-instructions.md", out)
            self.assertFalse((target / ".ai-context").exists())
            self.assertFalse((target / "CLAUDE.md").exists())
            self.assertFalse((target / "AGENTS.md").exists())
            self.assertFalse((target / ".github").exists())

    def test_print_snippets_works_when_ai_context_already_exists(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / ".ai-context").mkdir()
            (target / ".ai-context" / "00-overview.md").write_text(
                "existing context",
                encoding="utf-8",
            )
            (target / "CLAUDE.md").write_text("existing entry", encoding="utf-8")

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = init.main(_base_argv(target, ["--print-snippets"]))

            self.assertEqual(rc, 0)
            self.assertIn("CLAUDE.md", buf.getvalue())
            self.assertEqual(
                (target / ".ai-context" / "00-overview.md").read_text(encoding="utf-8"),
                "existing context",
            )
            self.assertEqual(
                (target / "CLAUDE.md").read_text(encoding="utf-8"),
                "existing entry",
            )
            self.assertFalse((target / "AGENTS.md").exists())


def _write_legacy_context(target: Path):
    ai = target / ".ai-context"
    ai.mkdir()
    (ai / "README.md").write_text(
        "# .ai-context/\n\nold navigation\n\n## 文件导航\nold table\n",
        encoding="utf-8",
    )
    (ai / "02-conventions.md").write_text(
        "# 02\n\n## AI 助手协作约定\n- old user-specific rule\n",
        encoding="utf-8",
    )
    (ai / "05-current-state.md").write_text(
        "# 05\n\n## ✅ Done\n- existing done\n\n## ⏭️ Next\n- existing next\n\n## ⚠️ Blocked\n- none\n",
        encoding="utf-8",
    )
    (ai / "06-session-log.md").write_text(
        "# 06\n\n> **条目格式 / Entry format**:\n>\n> ```\n"
        "> ## YYYY-MM-DD · <助手名 / Assistant name>\n"
        "> **完成 / Done**: ...\n"
        "> **进行中 / In progress**: ...\n"
        "> **下一步建议 / Next**: ...\n"
        "> **注意 / Watch out**: ...\n"
        "> ```\n\n"
        "## 2026-01-01 · Codex\n"
        "**完成 / Done**: legacy session history\n",
        encoding="utf-8",
    )
    for relpath in ("CLAUDE.md", "AGENTS.md", ".github/copilot-instructions.md"):
        path = target / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Entry\n\n**技术栈**: Python\n\n## 会话交接三条铁律(不可协商)\n"
            "1. **进入会话**:old rule\n",
            encoding="utf-8",
        )


class TestMainDoctor(unittest.TestCase):
    def test_doctor_generated_context_ok(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stdout(io.StringIO()):
                init.main(_base_argv(target))
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = init.main(["--target", str(target), "--doctor"])
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn("OK:", out)
            self.assertIn("MISSING:\n  - (none)", out)
            self.assertIn("OUTDATED:\n  - (none)", out)

    def test_doctor_missing_context_returns_1_without_project_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = init.main(["--target", str(target), "--doctor"])
            self.assertEqual(rc, 1)
            self.assertIn(".ai-context/", buf.getvalue())

    def test_doctor_outdated_protocol_returns_1(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stdout(io.StringIO()):
                init.main(_base_argv(target))
            path = target / ".ai-context" / "02-conventions.md"
            text = path.read_text(encoding="utf-8").replace("AI Autonomy Policy", "AI Policy")
            path.write_text(text, encoding="utf-8")

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = init.main(["--target", str(target), "--doctor"])
            self.assertEqual(rc, 1)
            self.assertIn("OUTDATED:", buf.getvalue())
            self.assertIn("AI Autonomy Policy", buf.getvalue())


class TestMainUpgrade(unittest.TestCase):
    def test_upgrade_refuses_without_ai_context(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = init.main(["--target", str(target), "--upgrade"])
            self.assertEqual(rc, 2)
            self.assertIn(".ai-context/ not found", err.getvalue())

    def test_upgrade_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            _write_legacy_context(target)
            before = (target / ".ai-context" / "02-conventions.md").read_text(encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = init.main(["--target", str(target), "--upgrade", "--dry-run"])
            self.assertEqual(rc, 0)
            self.assertIn("[upgrade dry-run]", buf.getvalue())
            self.assertEqual(
                (target / ".ai-context" / "02-conventions.md").read_text(encoding="utf-8"),
                before,
            )
            self.assertEqual(list(target.rglob("*.bak-*")), [])

    def test_upgrade_patches_legacy_context_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            _write_legacy_context(target)

            with redirect_stdout(io.StringIO()):
                rc = init.main(["--target", str(target), "--upgrade"])
            self.assertEqual(rc, 0)

            conventions = (target / ".ai-context" / "02-conventions.md").read_text(
                encoding="utf-8"
            )
            session_log = (target / ".ai-context" / "06-session-log.md").read_text(
                encoding="utf-8"
            )
            entry = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("old user-specific rule", conventions)
            self.assertIn("AI Autonomy Policy", conventions)
            self.assertIn("Completion Report / Definition of Done", conventions)
            self.assertIn("legacy session history", session_log)
            self.assertIn("本文件是给下一位 AI 的 baton", session_log)
            self.assertIn("**改动文件 / Changed files**", session_log)
            self.assertIn("Done / Changed files / Validation / Next or risks", entry)

            backups = list(target.rglob("*.bak-*"))
            self.assertGreaterEqual(len(backups), 1)

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = init.main(["--target", str(target), "--upgrade"])
            self.assertEqual(rc, 0)
            self.assertIn("up to date", buf.getvalue())
            self.assertEqual(len(list(target.rglob("*.bak-*"))), len(backups))


class TestArgValidation(unittest.TestCase):
    def test_force_and_merge_mutually_exclusive(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    init.main(_base_argv(target, ["--force", "--merge"]))

    def test_print_snippets_rejects_write_modes(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    init.main(_base_argv(target, ["--print-snippets", "--merge"]))

    def test_adopt_rejects_other_write_modes(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            for extra in (
                ["--adopt", "--force"],
                ["--adopt", "--merge"],
                ["--adopt", "--print-snippets"],
            ):
                with self.subTest(extra=extra):
                    with redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit):
                            init.main(_base_argv(target, extra))

    def test_adopt_rejects_upgrade_mode(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    init.main(["--target", str(target), "--upgrade", "--adopt"])

    def test_doctor_rejects_init_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    init.main(["--target", str(target), "--doctor", "--name", "demo"])

    def test_upgrade_allows_only_dry_run_as_extra_flag(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    init.main(["--target", str(target), "--upgrade", "--merge"])

    def test_invalid_slug_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    init.main([
                        "--target", str(target),
                        "--name", "bad name with spaces",
                        "--description", "y",
                        "--stage", "new",
                        "--as", "claude",
                    ])


class TestTargetValidation(unittest.TestCase):
    def test_nonexistent_target_exits(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                init.main([
                    "--target", str(Path(tempfile.gettempdir()) / "definitely-not-here-xyz"),
                    "--name", "x",
                    "--description", "y",
                    "--stage", "new",
                    "--as", "claude",
                ])

    def test_file_as_target_exits(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
        try:
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    init.main([
                        "--target", path,
                        "--name", "x",
                        "--description", "y",
                        "--stage", "new",
                        "--as", "claude",
                    ])
        finally:
            Path(path).unlink()


class TestListPacks(unittest.TestCase):
    def test_list_packs_prints_every_known_pack_file(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = init.main(["--list-packs"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        # Every unique file in GLOSSARY_PACKS should appear in the output.
        for filename in set(init.GLOSSARY_PACKS.values()):
            self.assertIn(filename, out, f"missing pack file in output: {filename}")

    def test_list_packs_groups_aliases(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            init.main(["--list-packs"])
        out = buf.getvalue()
        # The three gnss-sdr aliases should all appear together on one line
        # (grouped by filename).
        for alias in ("gnss", "sdr", "gnss-sdr"):
            self.assertIn(alias, out)

    def test_list_packs_does_not_require_other_args(self):
        # --list-packs must work before any validation — no --name, --target, etc.
        with redirect_stdout(io.StringIO()):
            rc = init.main(["--list-packs"])
        self.assertEqual(rc, 0)


class TestDomainsAllMissWarning(unittest.TestCase):
    def test_all_unmatched_domains_trigger_info_message(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = init.main(_base_argv(target, ["--domains", "foo,bar"]))
            self.assertEqual(rc, 0)
            self.assertIn("none of --domains", err.getvalue())
            self.assertIn("--list-packs", err.getvalue())

    def test_partial_miss_stays_silent(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = init.main(_base_argv(target, ["--domains", "web,nonexistent"]))
            self.assertEqual(rc, 0)
            # Documented design: per-keyword unknowns stay silent when at
            # least one matched.
            self.assertNotIn("none of --domains", err.getvalue())

    def test_no_domains_no_message(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                init.main(_base_argv(target))
            self.assertNotIn("none of --domains", err.getvalue())


class TestGlossaryEndToEnd(unittest.TestCase):
    def test_web_domain_injects_pack_into_glossary_file(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stdout(io.StringIO()):
                init.main(_base_argv(target, ["--domains", "web"]))
            glossary = (target / ".ai-context" / "03-glossary.md").read_text(encoding="utf-8")
            self.assertIn("REST", glossary)
            self.assertNotIn(init.GLOSSARY_SLOT, glossary)

    def test_unmatched_domain_still_succeeds(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rc = init.main(_base_argv(target, ["--domains", "nonexistent"]))
            self.assertEqual(rc, 0)
            glossary = (target / ".ai-context" / "03-glossary.md").read_text(encoding="utf-8")
            self.assertNotIn(init.GLOSSARY_SLOT, glossary)


if __name__ == "__main__":
    unittest.main()
