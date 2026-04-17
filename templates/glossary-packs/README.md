# Glossary packs

Each file in this directory is a small Markdown fragment that gets injected into the project's `03-glossary.md` when a user passes `--domains <keyword>` to `init.py`.

Currently shipped:

| Keyword(s)         | File               | Covers                                       |
| ------------------ | ------------------ | -------------------------------------------- |
| `web`              | `web-fullstack.md` | REST, GraphQL, JWT, CORS, ORM, SSR, etc.     |
| `ml`               | `ml-basics.md`     | epoch, batch size, overfitting, checkpoint…  |
| `gnss-sdr`, `gnss`, `sdr` | `gnss-sdr.md` | BOC, Gold code, PCPS, PRN, Doppler, USRP…    |

Multiple packs can be applied together: `--domains "web,ml"` injects both.

## Format

```markdown
## <Domain display name>
- **<Term>** (<Abbreviation expansion if any>): concise definition, 1-2 lines max.
- **<Term>**: ...
```

## Adding a new pack

See the "Adding a glossary pack" section of `../../CONTRIBUTING.md` at the skill root. Short version: drop a new `.md` here, add a mapping entry to `GLOSSARY_PACKS` in `scripts/init.py`, update `README.md` and `CHANGELOG.md`.
