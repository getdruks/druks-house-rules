"""The nudge outside Druks, for the CLI and the plugin: the same template and pool as
the ``house_rules.nudge`` agent, the model through the Claude Code CLI."""

import importlib.resources
import pathlib

import jinja2
import yaml

from . import checkout, moves
from .exceptions import UnknownEntryError

TEMPLATES = importlib.resources.files(__package__).joinpath("templates")
ENTRIES = yaml.safe_load(TEMPLATES.joinpath("pool.yml").read_text())
# The loader shape Druks mounts an app's templates under, so the include resolves alike.
ENVIRONMENT = jinja2.Environment(
    loader=jinja2.PrefixLoader({"house_rules": jinja2.FileSystemLoader(str(TEMPLATES))}),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def nudge(root: pathlib.Path, base: str, task: str) -> dict | None:
    """The nudge for the working tree against the base: the entry id, its phrase
    verbatim, and where the situation shows, or nothing."""
    repository = checkout.Checkout(root)
    diff = repository.diff(repository.merge_base(base)) or "nothing"
    prompt = ENVIRONMENT.get_template("house_rules/nudge.md").render(diff=diff, task=task)
    answer = moves.ask(prompt)
    if not answer:
        return
    choice = moves.parse(answer)
    entry = choice["entry"]
    if not entry:
        return
    if not 1 <= entry <= len(ENTRIES):
        raise UnknownEntryError(f"the pool holds {len(ENTRIES)} entries, not entry {entry}")
    return {"entry": entry, "phrase": ENTRIES[entry - 1]["phrase"], "where": choice["where"]}
