"""R14. No link to a Notion page or a Linear ticket in the repository, commits, or pull request."""

import re

from druks_house_rules import changes
from druks_house_rules.findings import Finding

LINKS = {
    "Linear ticket": re.compile(r"https://linear\.app/[^/\s]+/issue/\S+"),
    "Notion page": re.compile(
        r"https://(www\.)?notion\.so/\S+|https://(app\.|www\.)?notion\.com/p/\S+"
    ),
}


def check(change: changes.Change) -> list[Finding]:
    findings = []
    for path, text in change.texts():
        findings.extend(_scan(path, text))
    for commit in change.commits:
        findings.extend(_scan(f"commit:{commit.sha[:12]}", f"{commit.subject}\n{commit.body}"))
    if change.pull_request:
        findings.extend(_scan("pr-title", change.pull_request.title))
        findings.extend(_scan("pr-body", change.pull_request.body))
    return findings


def _scan(path: str, text: str) -> list[Finding]:
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in LINKS.items():
            if pattern.search(line):
                findings.append(Finding(path, number, "R14", f"link to a {kind}; keep it private"))
    return findings
