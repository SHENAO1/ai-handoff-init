"""Tests for scripts/init.py.

Uses stdlib unittest to stay consistent with the script's stdlib-only policy.
Run with: python -m unittest discover -s tests
"""

from __future__ import annotations

import argparse
import io
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
