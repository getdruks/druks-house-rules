"""The rules ast-grep finds: rule-2, rule-3, R21, R13, R11.

Each rule is one YAML file in ``patterns/``. A line that must keep an ``is None``
carries ``# ast-grep-ignore: rule-2``.
"""

import json
import pathlib
import shutil
import subprocess
import sys

from . import changes
from .exceptions import HouseRulesError
from .findings import Finding

PATTERNS = pathlib.Path(__file__).parent / "patterns"


def check(change: changes.Change) -> list[Finding]:
    paths = [path for path in change.files if path.endswith(".py")]
    if not paths:
        return []
    rules = "\n---\n".join(path.read_text() for path in sorted(PATTERNS.glob("*.yml")))
    result = subprocess.run(
        [_binary(), "scan", "--inline-rules", rules, "--json=compact", *paths],
        cwd=change.root,
        check=True,
        capture_output=True,
        text=True,
    )
    findings = []
    for match in json.loads(result.stdout):
        rule = match["ruleId"]
        module = match["metaVariables"]["single"].get("MODULE", {}).get("text")
        if rule == "R21" and module in change.config.import_modules:
            continue
        findings.append(
            Finding(match["file"], match["range"]["start"]["line"] + 1, rule, match["message"])
        )
    return findings


def _binary() -> str:
    """The ast-grep binary the ast-grep-cli package installs beside the interpreter."""
    beside_python = pathlib.Path(sys.executable).parent / "ast-grep"
    if beside_python.is_file():
        return str(beside_python)
    binary = shutil.which("ast-grep")
    if not binary:
        raise HouseRulesError("ast-grep is missing. Install the ast-grep-cli package.")
    return binary
