# Changelog

All notable changes to this project will be documented in this file. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
