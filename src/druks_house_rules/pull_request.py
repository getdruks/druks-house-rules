"""R27. A pull request body says what the change is and its mechanism, nothing else."""

import re

from druks_house_rules import changes
from druks_house_rules.findings import Finding

SECTION = re.compile(r"^#+\s*(verification|test|risk)", re.IGNORECASE)
LINK = re.compile(r"notion\.com|linear\.app|co-authored-by", re.IGNORECASE)


def check(change: changes.Change) -> list[Finding]:
    if not change.pull_request:
        return []
    findings = []
    for number, line in enumerate(change.pull_request.body.splitlines(), start=1):
        if SECTION.match(line):
            findings.append(Finding("pr-body", number, "R27", f"section {line.strip()!r}; drop it"))
        if LINK.search(line):
            findings.append(Finding("pr-body", number, "R27", f"line: {line.strip()}"))
    return findings
