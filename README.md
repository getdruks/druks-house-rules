# druks-house-rules

The hard rules every Druks repository holds a change to, as one check. A rule
here is one a program can decide. The rules that need judgment live in each
repository's `.druks/software_factory/review.md` and the Druks reviewer applies them.

## Install

```bash
uv pip install "git+https://github.com/getdruks/druks-house-rules@v0.0.4"
```

## Check a change

```bash
druks-house-rules check --base origin/main
druks-house-rules check --base origin/main --pr-title "$TITLE" --pr-body "$BODY"
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

With `--json`, it prints the findings as one JSON array of `path`, `line`,
`rule`, and `message`. It exits 2 when the configuration is malformed and 3
when it is missing.

## Rules

The rule ids come from the Druks rulebook. `rule-<n>` is item `n` of the
checklist. `R<n>` is rule `n` of the rules the corrections added.

| Id | Rule | How |
| --- | --- | --- |
| R14 | No link to a Notion page or a Linear ticket in the repository, the commits, or the pull request text. | `linear.app/<workspace>/issue/`, `notion.so/`, and `notion.com/p/` URLs. Service hosts such as `api.linear.app` pass. |
| R28 | One commit above the base. A subject that starts with a ticket is `<ticket> -- <what the change does>`. No AI attribution and no pull request number. A co-author line for a person passes. | `git log` above the merge base. |
| R27 | The pull request body says what the change is and its mechanism. No verification, test, or risk section, no attribution. | `--pr-body`. |
| rule-3 | `isinstance` only at a trust boundary. | Paths under `webhooks/`, `apis/`, or `harnesses/` are boundaries. Add others as exceptions. |
| rule-2 | Truthiness, never `is None`. | Mark a line where `None` is a distinct value with `# ast-grep-ignore: rule-2`. |
| rule-1 | Bare `return`, never `return None`. | ruff `RET501`. |
| R21 | Four or more names from one module: import the module. | `typing` and the `R21` `modules` key are exempt. `__init__.py` and `from . import` are exempt. |
| R23 | No function-level import. | ruff `PLC0415`. |
| R5 | No catch of `Exception` or bare `except`. | ruff `BLE001`, `E722`. |
| R13 | Every function in `workflows.py`, `services.py`, and `tasks.py` is async. | Class methods, static methods, properties, setters, and dunder methods stay sync. |
| R11 | A `@step` marks a replay checkpoint. | A step whose body is one call to `enqueue`, a logger, or `set_run_phase` fails. |
| R25 | No module named `deps`, `helpers`, `utils`, `common`, or `misc`. | Added files with `--base`; all tracked files without. |
| R16 | Author-surface modules never import an app. Apps import only the public modules. | The `R16` key in the configuration. |

rule-2, rule-3, R21, R13, and R11 are ast-grep rules, one YAML file each in
`src/druks_house_rules/patterns/`. rule-1, R23, and R5 are ruff rules. R16
reads the import graph that grimp builds. R14, R27, R28, and R25 read text,
the pull request, and git.

Every rule has a positive and a negative fixture in `tests/fixtures/<rule>/`.
The test suite runs each through the CLI.

## The driver pool

`src/druks_house_rules/pool.yml` holds the phrases Paulo uses to correct an
agent, one entry per phrase. An entry has `phrase` (his words, with code names
and personal remarks removed, so the phrase steers without naming code the
target does not have), `theme` (one of `overengineering`, `primitives`,
`naming`, `wrong layer`, `steps`, `tests`, `imports`, `narration`, `scope`),
`situation` (one sentence on what the agent had produced, described, not
quoted), and `count` (how many sessions he said it in). The pool is not a
checklist. A reviewer reads the rules above. A picker reads the pool to choose
the one phrase that fits an implementer's output, and the implementer finds
the problem itself. The test suite rejects an entry that misses a field or
names an unknown theme.

## Run in Druks

The `app` extra ships the Druks app `house_rules`. Druks receives the pull
request webhook of every repository the operator App is installed on. For each
pull request opened, pushed, edited, or marked ready for review, the app runs
the check in a sandbox VM that holds this package at the app's version and the
repository at the pull request head, with the pull request title and body, and
posts the check run `druks-house-rules` on the head commit: success with no
findings, failure with one annotation per finding and the findings as the
summary. A repository without `.druks/house_rules/config.yml` gets a neutral
check run. One head, title, and body gets one run; a redelivered webhook posts
nothing twice.

Install the extra in the Druks installation and build its sandbox template:

```bash
uv pip install "druks-house-rules[app] @ git+https://github.com/getdruks/druks-house-rules@v0.0.4"
druks init-db
druks sandboxes build
```

The App needs **Checks: Read and write**. To hold a repository to the rules,
install the operator App on it, put `.druks/house_rules/config.yml` in it, and
require the check `druks-house-rules` in its branch protection.

## Run in Claude Code

The plugin runs the same check in every Claude Code session, so the agent
reads a finding before it says the work is ready. Install it once:

```bash
claude plugin install druks-house-rules --marketplace getdruks/druks-house-rules
```

The plugin needs `uv`. Its first run installs this package, at the plugin's
version, into a virtual environment under the plugin's data directory. The
plugin carries no rule text; the rules come from the package. Outside a
repository that holds `.druks/house_rules/config.yml`, every hook answers nothing.

| Hook | What it does |
| --- | --- |
| PostToolUse on Edit, Write, and MultiEdit | Runs the check on the edited file and returns the findings. The edit stands. |
| PreToolUse on Bash | Denies with the rule text: R33 a `git commit` on `main`, R20 a test run piped into `tail`, `head`, or `grep`, R28 a commit message with AI attribution. Asks the owner before R35, a `gh pr merge` or `gh release`. |
| PreToolUse on ExitPlanMode | R1: denies a plan without a `prior_art` section, or one whose section does not name a module, class, setting, column, flag, or dependency the plan adds. |
| Stop | Holds the branch against `origin/main`: the check, the surface delta, and the moves pass. On any finding it blocks the stop once with the three lists, and lets the second stop through. |

The moves pass sends the catalog in `.druks/software_factory/review.md`, the
delta, and the diff to a small model through `claude -p` and asks which moves
apply, with the line. Without the catalog file, the pass is skipped. To run it
by hand:

```bash
druks-house-rules moves --base origin/main
```

## Configure a repository

Put `.druks/house_rules/config.yml` in the repository. An app owns
`.druks/<app>/`, and repository files under `.druks/` are YAML. Keys other than
these fail the check.

```yaml
# The rules to run. Without this key, every rule runs.
rules: [R14, R28, R27, rule-3, rule-2, rule-1, R21, R23, R5, R13, R11, R25, R16]

# Paths no rule reads. `*` stays inside one directory, `**` crosses directories.
exclude: [uv.lock, frontend/package-lock.json, backend/druks/migrations/versions/**]

R21:
  # Modules whose names a file may import in bulk, beside `typing`.
  modules: [fastapi, sqlalchemy, pydantic]

R16:
  root: backend
  package: druks
  author_surface: [druks.workflows, druks.workspaces, druks.agents, druks.events, druks.signals, druks.db, druks.schemas, druks.prompts, druks.durable, druks.apps, druks.ui, druks.webhooks]
  public: [druks.workflows, druks.workspaces, druks.agents, druks.events, druks.signals, druks.db, druks.schemas, druks.prompts, druks.durable, druks.apps, druks.ui, druks.webhooks, druks.core, druks.chat]
  apps: [druks.contrib]
  # Imports the contract tolerates, as `importer -> imported` module globs.
  ignore_imports: ["druks.contrib.** -> druks.accounts.**"]

# Paths a rule does not read, by rule id.
exceptions:
  rule-3: [backend/druks/settings.py]
  R13: [backend/druks/workflows.py]
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

The tests of the app need Postgres on `localhost:5432` with user and password
`druks` and the `druks_test` database.

```bash
uv sync --extra app
uv run ruff check
uv run ruff format --check
uv run druks check-app house_rules
uv run pytest
uv run druks-house-rules check
```
