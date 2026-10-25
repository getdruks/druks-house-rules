# druks-house-rules

The hard rules every Druks repository holds a change to, as one check. A rule
here is one a program can decide. The rules that need judgment live in each
repository's `.druks/software_factory/review.md` and the Druks reviewer applies them.

## Install

```bash
uv pip install "git+https://github.com/getdruks/druks-house-rules@v0.1.0"
```

The repository is private. In CI, pass a token with read access to it.

## Check a change

```bash
druks-house-rules check --base origin/main
druks-house-rules check --base origin/main --pr-title "$TITLE" --pr-body-file body.md
druks-house-rules check
```

With `--base`, the check reads the files the working tree changes against the
merge base, and the commits above it. Without `--base`, it reads every tracked
file and no commits. The pull request title and body are optional; the rules
about them run only when they are given.

The check prints one line per finding and exits 1 when there is one:

```
backend/druks/mcp/helpers.py:1 R25 helpers.py names a mechanism; name the noun
backend/druks/usage/routes.py:139 rule-2 use truthiness, not "is None"; mark a real sentinel with "# ast-grep-ignore: rule-2"
commit:0f3a2c1d9e7b:1 R28 2 commits above the base; squash them into one
```

It exits 2 when the configuration is missing or malformed.

## Rules

The rule ids come from the Druks rulebook. `rule-<n>` is item `n` of the
checklist. `R<n>` is rule `n` of the rules the corrections added.

| Id | Rule | How |
| --- | --- | --- |
| R14 | No word from the repository's denylist in code, docs, or pull request text. | `[R14] words` in the configuration. Case does not matter. |
| R28 | One commit above the base. A subject that starts with a ticket is `<ticket> -- <what the change does>`. No attribution trailer, no pull request number. | `git log` above the merge base. |
| R27 | The pull request body says what the change is and its mechanism. No verification, test, or risk section, no plan links, no attribution. | `--pr-body-file`. |
| rule-3 | `isinstance` only at a trust boundary. | Paths under `webhooks/`, `apis/`, or `harnesses/` are boundaries. Add others as exceptions. |
| rule-2 | Truthiness, never `is None`. | Mark a line where `None` is a distinct value with `# ast-grep-ignore: rule-2`. |
| rule-1 | Bare `return`, never `return None`. | ruff `RET501`. |
| R21 | Four or more names from one module: import the module. | `typing` and `[R21] modules` are exempt. `__init__.py` is exempt. |
| R23 | No function-level import. | ruff `PLC0415`. |
| R5 | No catch of `Exception` or bare `except`. | ruff `BLE001`, `E722`. |
| R13 | Every function in `workflows.py`, `services.py`, and `tasks.py` is async. | Class methods, static methods, properties, setters, and dunder methods stay sync. |
| R11 | A `@step` marks a replay checkpoint. | A step whose body is one call to `enqueue`, a logger, or `set_run_phase` fails. |
| R25 | No module named `deps`, `helpers`, `utils`, `common`, or `misc`. | Added files with `--base`; all tracked files without. |
| R16 | Author-surface modules never import an app. Apps import only the public modules. | `[R16]` in the configuration. |

rule-2, rule-3, R21, R13, and R11 are ast-grep rules, one YAML file each in
`src/druks_house_rules/patterns/`. rule-1, R23, and R5 are ruff rules. R16
reads the import graph that grimp builds. R14, R27, R28, and R25 read text,
the pull request, and git.

Every rule has a positive and a negative fixture in `tests/fixtures/<rule>/`.
The test suite runs each through the CLI.

## Configure a repository

Put `druks-house-rules.toml` in the repository root. Keys other than these fail
the check.

```toml
# The rules to run. Without this key, every rule runs.
rules = ["R14", "R28", "R27", "rule-3", "rule-2", "rule-1", "R21", "R23", "R5", "R13", "R11", "R25", "R16"]

# Paths no rule reads. `*` stays inside one directory, `**` crosses directories.
exclude = ["uv.lock", "frontend/package-lock.json", "backend/druks/migrations/versions/**"]

[R14]
words = ["linkedin", "twitter", "x-me", "clinic", "notion.com", "linear.app", "is_managed", "druks-cloud", "portal"]

[R21]
# Modules whose names a file may import in bulk, beside `typing`.
modules = ["fastapi", "sqlalchemy", "pydantic"]

[R16]
root = "backend"
package = "druks"
author_surface = ["druks.workflows", "druks.workspaces", "druks.agents", "druks.events", "druks.signals", "druks.db", "druks.schemas", "druks.prompts", "druks.durable", "druks.apps", "druks.ui", "druks.webhooks"]
public = ["druks.workflows", "druks.workspaces", "druks.agents", "druks.events", "druks.signals", "druks.db", "druks.schemas", "druks.prompts", "druks.durable", "druks.apps", "druks.ui", "druks.webhooks", "druks.core", "druks.chat"]
apps = ["druks.contrib"]
# Imports the contract tolerates, as `importer -> imported` module globs.
ignore_imports = ["druks.contrib.** -> druks.accounts.**"]

# Paths a rule does not read, by rule id.
[exceptions]
rule-3 = ["backend/druks/settings.py"]
R13 = ["backend/druks/workflows.py"]
```

## Print the surface a change adds

```bash
druks-house-rules delta --base origin/main
```

The command prints one line per new module, class, public function, settings
key, column, migration, dependency, `try/except`, and optional parameter, then
the ratio of added test lines to added source lines. It never fails. A
settings key is an annotated field of a class whose name ends in `Settings`. A
column is a field assigned from `mapped_column` or `Column`.

```
backend/druks/notes.py:1 module backend.druks.notes
backend/druks/models.py:40 class Note
backend/druks/settings.py:12 setting Settings.notes_limit
tests/source ratio 0.50 (6 test lines, 12 source lines)
```

## Develop

```bash
uv sync
uv run ruff check
uv run ruff format --check
uv run pytest
uv run druks-house-rules check
```
