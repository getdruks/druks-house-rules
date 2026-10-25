"""R14. Words that never appear in a repository's code, docs, or pull request text."""

import re

from druks_house_rules import changes
from druks_house_rules.findings import Finding


def check(change: changes.Change) -> list[Finding]:
    patterns = [
        (word, re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE))
        for word in change.config.denylist
    ]
    findings = []
    for path, text in change.texts():
        findings.extend(_scan(path, text, patterns))
    if change.pull_request:
        findings.extend(_scan("pr-title", change.pull_request.title, patterns))
        findings.extend(_scan("pr-body", change.pull_request.body, patterns))
    return findings


def _scan(path: str, text: str, patterns: list[tuple[str, re.Pattern[str]]]) -> list[Finding]:
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        for word, pattern in patterns:
            if pattern.search(line):
                findings.append(
                    Finding(path, number, "R14", f'"{word}" is on the denylist; remove it')
                )
    return findings
