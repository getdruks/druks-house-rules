"""The rules ruff checks: rule-1 bare return, R23 function-level imports, R5 catches,
R39 parent-relative imports."""

import json
import pathlib
import subprocess
import sys

from . import changes
from .findings import Finding

CODES = {
    "RET501": "rule-1",
    "PLC0415": "R23",
    "BLE001": "R5",
    "E722": "R5",
    "TID252": "R39",
}


def check(change: changes.Change) -> list[Finding]:
    paths = [path for path in change.files if path.endswith(".py")]
    if not paths:
        return []
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--isolated",
            "--exit-zero",
            "--select",
            ",".join(CODES),
            "--target-version",
            "py311",
            "--output-format",
            "json",
            *paths,
        ],
        cwd=change.root,
        check=True,
        capture_output=True,
        text=True,
    )
    findings = []
    for entry in json.loads(result.stdout):
        rule = CODES.get(entry["code"] or "", "syntax")
        path = pathlib.Path(entry["filename"]).relative_to(change.root).as_posix()
        findings.append(Finding(path, entry["location"]["row"], rule, message(entry)))
    return findings


def message(entry: dict) -> str:
    """Ruff's text, or for R39 the absolute import ruff resolves when the file is in a package."""
    fix = entry["fix"]
    if entry["code"] == "TID252" and fix:
        return f"parent-relative import; write {fix['edits'][0]['content']}"
    return entry["message"]
