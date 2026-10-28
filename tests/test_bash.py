"""The process rules on a Bash command: R33, R35, R20, R28."""

import pytest

from druks_house_rules import bash


@pytest.mark.parametrize(
    ("command", "branch", "rules"),
    [
        ('git commit -m "DRU-1 -- Add notes"', "main", ["R33"]),
        ("git push -u origin main", "main", []),
        ('cd backend && git -C .. commit -m "DRU-1 -- Add notes"', "main", ["R33"]),
        ('git commit -m "DRU-1 -- Add notes"', "dru-1-notes", []),
        ("git push -u origin dru-1-notes", "dru-1-notes", []),
        ("gh pr merge 12 --squash", "dru-1-notes", ["R35"]),
        ("gh release create v0.0.2", "dru-1-notes", ["R35"]),
        ("git tag v0.0.2", "dru-1-notes", []),
        ("gh pr view 12", "dru-1-notes", []),
        ("uv run pytest backend/ | tail -20", "dru-1-notes", ["R20"]),
        ("pytest 2>&1 | head -50", "dru-1-notes", ["R20"]),
        ("npm --prefix frontend test | grep FAIL", "dru-1-notes", ["R20"]),
        ("uv run pytest backend/", "dru-1-notes", []),
        ("git log | grep DRU-1", "dru-1-notes", []),
        (
            'git commit -m "DRU-1 -- Add notes\n\nCo-Authored-By: Claude <noreply@anthropic.com>"',
            "dru-1-notes",
            ["R28"],
        ),
        (
            'git commit -m "DRU-1 -- Add notes\n\nCo-Authored-By: Dana <dana@example.com>"',
            "dru-1-notes",
            [],
        ),
        ("git commit -m 'DRU-1 -- Add notes' && git push", "main", ["R33"]),
    ],
)
def test_command(command, branch, rules):
    assert [finding.rule for finding in bash.check(command, branch)] == rules


def test_unbalanced_quotes_still_read():
    findings = bash.check("git commit -m 'DRU-1 -- Add notes", "main")
    assert [finding.rule for finding in findings] == ["R33"]
