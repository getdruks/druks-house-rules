"""R28. One commit above the base, with a plain subject and no attribution."""

import re

from . import changes
from .findings import Finding

TICKET = re.compile(r"^[A-Z]+-\d+")
TICKET_SUBJECT = re.compile(r"^[A-Z]+-\d+ -- \S")
PULL_REQUEST_NUMBER = re.compile(r"#\d+")
ATTRIBUTION = re.compile(r"co-authored-by|claude-session|generated with|claude code", re.I)


def check(change: changes.Change) -> list[Finding]:
    findings = []
    if len(change.commits) > 1:
        findings.append(
            Finding(
                f"commit:{change.commits[-1].sha[:12]}",
                1,
                "R28",
                f"{len(change.commits)} commits above the base; squash them into one",
            )
        )
    for commit in change.commits:
        path = f"commit:{commit.sha[:12]}"
        if TICKET.match(commit.subject) and not TICKET_SUBJECT.match(commit.subject):
            findings.append(
                Finding(path, 1, "R28", "subject is '<ticket> -- <what the change does>'")
            )
        if PULL_REQUEST_NUMBER.search(commit.subject):
            findings.append(
                Finding(path, 1, "R28", "subject names a pull request number; GitHub adds it")
            )
        for number, line in enumerate(commit.body.splitlines(), start=2):
            if ATTRIBUTION.search(line):
                findings.append(Finding(path, number, "R28", f"attribution line: {line.strip()}"))
    return findings
