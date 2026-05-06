# Changelog

All notable changes to this project will be documented in this file. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.2] — 2026-05-06

### Added
- Minimal GitHub Actions CI running the stdlib unit test suite, whitespace diff checks, and no-write CLI smoke tests.
- Version consistency tests that assert `scripts/init.py --version` and `SKILL.md` frontmatter both report `0.1.2`.
- `--print-snippets` CLI flag: renders and prints `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md` snippets only, without creating or modifying files. This is the safe path when a target project already has `.ai-context/`.

### Changed
- Aligned the skill frontmatter version, CLI `--version` output, README CLI references, changelog, and release workflow documentation for `0.1.2`.
- Release workflow now calls out pre-tag version checks across `SKILL.md`, CLI `--version`, and `CHANGELOG.md`.

## [0.1.1] — 2026-04-17

### Added
- `tests/test_init.py` — 49 stdlib `unittest` cases covering pure helpers (`render`, `load_glossary_injection`, `inject_glossary`, `build_context`, `detect_conflicts`, `build_plan`, `parse_domain_keywords`) and `main()` flow branches (`--dry-run`, `--merge`, `--force`, conflict exit codes, slug validation, target validation).
- `--list-packs` CLI flag: prints available glossary packs grouped by file, works without any other arguments.
- Info message on stderr when every `--domains` keyword fails to match a built-in pack (partial misses stay silent, per the documented silent-ignore design).
- `README.zh-CN.md` — a full Simplified Chinese guide with Windows/PowerShell examples, validation commands, and existing-project `--merge` guidance.

### Changed
- `templates/ai-context/06-session-log.md` entry labels are now bilingual (`完成 / Done`, `进行中 / In progress`, `下一步建议 / Next`, `注意 / Watch out`) to match the canonical format documented in `SKILL.md`. Example project `assets/example/todo-api/.ai-context/06-session-log.md` updated to match.
- `--target` is now validated immediately after argument parsing, before any interactive prompts — users no longer answer five questions only to be told the target directory is invalid.
- `CONTRIBUTING.md` now includes a detailed local commit and release workflow, including verification commands, staging guidance, and tag/push steps.
- `README.md` now links to the new Chinese README at the top so GitHub visitors can switch languages without changing the default English homepage.

### Removed
- Dead `mode` parameter from `detect_conflicts()`.
- Redundant `validate_args` checks for `--stage`, `--as`, and `--description` — already guaranteed non-empty by `argparse choices` + `interactive_fill()`.

## [0.1.0] — 2026-04-17

### Added
- Initial release.
- `.ai-context/` layout with 9 Markdown files (README, 00 overview → 07 known-issues).
- Three entry file templates: `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`, each under 20 lines.
- `CLAUDE.md` uses Claude Code's `@` reference syntax to auto-load `05-current-state.md` and `.ai-context/README.md`.
- Session log rotation convention: keep last 20 entries, archive the rest to `06-session-log-archive.md`.
- Three built-in glossary packs: `web`, `ml`, `gnss-sdr`.
- `scripts/init.py` — Python 3.8+ stdlib-only init script with `--dry-run`, `--force` (with auto-backup), `--merge`, and interactive prompts.
- Fully-rendered example project: `assets/example/todo-api/`.
- Trigger evaluation set (`evals/evals.json`) with 6 test cases covering explicit, implicit, and negative triggers.
