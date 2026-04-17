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

## Licensing

Contributions are accepted under the same [MIT License](LICENSE) as the rest of the project.
