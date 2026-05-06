# Contributing

Thanks for considering a contribution. The two most common contributions are:

1. Adding a new glossary pack for your domain.
2. Proposing improvements to the entry-file or `.ai-context/` templates.

## Adding a glossary pack

Glossary packs live in `templates/glossary-packs/<name>.md`. Each pack is a small Markdown fragment that gets injected into the project's `03-glossary.md` file when a user passes `--domains <name>`.

### Pack format

```markdown
## <Domain display name>
- **<Term>** (<Abbreviation expansion if any>): concise definition, 1-2 lines max.
- **<Term>**: ...
```

### Quality bar

- 10-20 terms per pack — enough to be useful, not so many it becomes a textbook.
- Definitions in the same language as the rest of the pack (English or Chinese, consistent per pack).
- Acronyms expanded on first mention.
- No external links (they rot). If a term has deep lore, just name it; readers can search.
- Terms should be domain-specific. Don't define "variable" or "function".

### Steps

1. Create `templates/glossary-packs/<name>.md` using one of the existing packs as a reference.
2. Register the keyword → filename mapping in `scripts/init.py`, in the `GLOSSARY_PACKS` dict near the top. Use lowercase keys.
3. Mention the new pack in `README.md` under "Glossary packs".
4. Add a line to `CHANGELOG.md` under "Unreleased".
5. If you want it tested, add one entry to `evals/evals.json` exercising the new pack.

### Worked example

Adding an `embedded` pack for embedded systems:

1. Create `templates/glossary-packs/embedded.md`:

   ```markdown
   ## Embedded systems
   - **MCU** (Microcontroller Unit): single-chip computer with CPU, memory, and peripherals.
   - **DMA** (Direct Memory Access): peripheral-to-memory transfer bypassing the CPU.
   - **RTOS** (Real-Time Operating System): scheduler with bounded, deterministic latency.
   ...
   ```

2. In `scripts/init.py`:

   ```python
   GLOSSARY_PACKS = {
       "web": "web-fullstack.md",
       "ml": "ml-basics.md",
       "gnss-sdr": "gnss-sdr.md",
       "gnss": "gnss-sdr.md",
       "sdr": "gnss-sdr.md",
       "embedded": "embedded.md",   # ← add this
   }
   ```

3. Update `README.md` and `CHANGELOG.md`.

That's it. No other files need to change.

## Template changes

The 9 files in `templates/ai-context/` and the 3 files in `templates/entry/` are load-bearing. Changes should consider:

- **Size budgets.** Entry files must stay under 20 lines after rendering. Dynamic files (`05`, `06`) should stay small per session.
- **Cross-assistant portability.** Features specific to one assistant (Claude Code's `@` syntax, Copilot's path-specific `applyTo` frontmatter) should never be required for the file to be useful to another assistant.
- **Placeholders.** Currently supported: `{{PROJECT_NAME}}`, `{{DESCRIPTION}}`, `{{TECH_STACK_INLINE}}`, `{{TECH_STACK_LIST}}`, `{{INIT_DATE}}`, `{{INIT_ASSISTANT}}`. Adding a new placeholder means changing `scripts/init.py` too.
- **Language.** Current templates use Chinese for AI-facing instructions. A future `--lang en` is planned; if you want it sooner, a PR adding a parallel `templates-en/` tree is welcome.

## Running the evals

The `evals/evals.json` file contains trigger test cases. If you change the skill's `description` in `SKILL.md`, re-run the evals to check trigger rates haven't regressed. See `scripts/run_loop.py` in the `skill-creator` skill for the tooling.

## Pull requests

- One pack or one template change per PR.
- Update `CHANGELOG.md`.
- Keep commits small and well-described.

## Commit and release workflow

Use this checklist when you are ready to commit local changes or cut a release tag.

### 1. Inspect the working tree

Start from the repository root:

```bash
git status
```

Make sure you understand every modified file before you stage anything. If you only meant to touch one area, review the diff:

```bash
git diff
git diff -- CONTRIBUTING.md
```

### 2. Update docs that travel with the change

Before committing:

- Update `CHANGELOG.md`. Keep unreleased work under `## [Unreleased]`, and before tagging move shipped notes into a dated `## [X.Y.Z]` section.
- If the CLI surface changed, update `README.md`.
- If the skill trigger or workflow changed, update `SKILL.md`.
- If templates or generated example output changed, update `assets/example/todo-api/` when needed.
- For releases, confirm the `SKILL.md` frontmatter `version`, `python scripts/init.py --version`, and `CHANGELOG.md` release section all agree.

### 3. Run local verification

For changes in `scripts/init.py`, templates, or user-facing docs, run the unit tests:

```bash
python -m unittest discover -s tests
```

The test suite includes version consistency coverage for `SKILL.md` and CLI `--version`; run the full discovery command before cutting a tag.

Also run the whitespace check used by CI:

```bash
git diff --check
```

If you changed CLI behavior, also run a quick smoke test in a temporary directory so you do not pollute the repository:

```powershell
$tmp = Join-Path $env:TEMP 'ai-handoff-smoke'
if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
python .\scripts\init.py --target $tmp --dry-run --name demo --description x --stage new --as claude
```

Useful extra checks for recent CLI additions:

```powershell
python .\scripts\init.py --version
python .\scripts\init.py --list-packs
python .\scripts\init.py --print-snippets --name demo --description x --stage new --as claude
python .\scripts\init.py --target $tmp --dry-run --name demo --description x --stage new --as claude --domains "foo,bar"
python .\scripts\init.py --target E:\definitely-not-here-xyz --name demo --description x --stage new --as claude
```

Expected behavior:

- `python -m unittest discover -s tests` ends with `OK`.
- `git diff --check` exits cleanly.
- `--version` prints the release version, for example `ai-handoff-init 0.1.2`.
- `--list-packs` prints the available glossary packs.
- `--print-snippets` prints entry snippets and writes no files.
- Unknown `--domains` values print one `info:` line on stderr but still complete the dry-run in an empty target.
- A bad `--target` fails immediately before any interactive prompts.

### 4. Stage deliberately

Stage only the files that belong to the change:

```bash
git add CONTRIBUTING.md CHANGELOG.md
```

If the change is larger, prefer explicit paths over `git add .` so unrelated files do not slip into the commit.

### 5. Write a clear commit message

Commit messages should describe the shipped change, not the debugging journey.

Good examples:

- `Document commit and release workflow`
- `Add embedded glossary pack`
- `Validate --target before interactive prompts`

Then commit:

```bash
git commit -m "Document commit and release workflow"
```

### 6. Tag only after the commit exists

Do not create a release tag on a dirty working tree. First confirm the tree is clean and the new commit is in place:

```bash
git status
git log --oneline -1
```

Then create the version tag:

```bash
git tag v0.1.2
```

For later releases, replace `v0.1.2` with the intended `vX.Y.Z`.

If you tagged the wrong commit, delete the local tag and recreate it before pushing:

```bash
git tag -d v0.1.2
git tag v0.1.2
```

### 7. Push branch and tag

Push the commit first, then the tag:

```bash
git push origin <branch-name>
git push origin v0.1.2
```

Or push all local tags explicitly if that is your normal workflow:

```bash
git push origin --tags
```

### 8. Final release sanity check

Before announcing a release, verify:

- `git status` is clean.
- `git tag --list` includes the new version.
- `CHANGELOG.md` matches what actually shipped.
- The commit referenced by the tag is the one you intended to release.

## Licensing

Contributions are accepted under the same [MIT License](LICENSE) as the rest of the project.
