"""The rule registry in evidence order, and the one check that runs it."""

from collections.abc import Callable

from druks_house_rules import changes
from druks_house_rules import commits
from druks_house_rules import imports
from druks_house_rules import modules
from druks_house_rules import patterns
from druks_house_rules import private_links
from druks_house_rules import pull_request
from druks_house_rules import ruff_rules
from druks_house_rules.findings import Finding

Rule = Callable[[changes.Change], list[Finding]]

RULES: dict[str, Rule] = {
    "R14": private_links.check,
    "R28": commits.check,
    "R27": pull_request.check,
    "rule-3": patterns.check,
    "rule-2": patterns.check,
    "rule-1": ruff_rules.check,
    "R21": patterns.check,
    "R23": ruff_rules.check,
    "R5": ruff_rules.check,
    "R13": patterns.check,
    "R11": patterns.check,
    "R25": modules.check,
    "R16": imports.check,
}


def check(change: changes.Change) -> list[Finding]:
    """Every finding of every configured rule, less the configured exceptions, sorted."""
    enabled = set(change.config.rules)
    findings = set()
    for rule in {RULES[name] for name in enabled}:
        for finding in rule(change):
            if finding.rule in enabled or finding.rule == "syntax":
                findings.add(finding)
    return sorted(
        finding for finding in findings if not change.config.excepted(finding.rule, finding.path)
    )
