"""The process rules on a Bash command: R33, R35, R20, R27."""

import pathlib

import pytest

from druks_house_rules import bash, checkout


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
            [],
        ),
        ("git commit -m 'DRU-1 -- Add notes' && git push", "main", ["R33"]),
    ],
)
def test_command(command, branch, rules, monkeypatch):
    monkeypatch.setattr(checkout.Checkout, "branch", lambda self: branch)
    findings = bash.check(command, pathlib.Path("."))
    assert [finding.rule for finding in findings] == rules


def test_unbalanced_quotes_still_read(monkeypatch):
    monkeypatch.setattr(checkout.Checkout, "branch", lambda self: "main")
    findings = bash.check("git commit -m 'DRU-1 -- Add notes", pathlib.Path("."))
    assert [finding.rule for finding in findings] == ["R33"]


@pytest.mark.parametrize(
    ("command", "rules"),
    [
        ("git -C {branch} commit -m notes", []),
        ("cd {branch} && git commit -m notes", []),
        ("cd {branch} && git -C {main} commit -m notes", ["R33"]),
        ("git -C {branch} log && git commit -m notes", ["R33"]),
        ("git -C $CHECKOUT commit -m notes", ["R33"]),
    ],
)
def test_a_commit_holds_the_branch_it_lands_on(command, rules, tmp_path, monkeypatch):
    main = tmp_path / "main"
    branch = tmp_path / "branch"
    main.mkdir()
    branch.mkdir()
    monkeypatch.setattr(
        checkout.Checkout, "branch", lambda self: "main" if self.root == main else "notes"
    )
    findings = bash.check(command.format(main=main, branch=branch), main)
    assert [finding.rule for finding in findings] == rules


HEREDOC = "\"$(cat <<'EOF'\nAdds notes.\n\n{text}\nEOF\n)\""


@pytest.mark.parametrize(
    "command",
    [
        'gh pr create --title Notes --body "## Verification"',
        'gh pr create --title Notes -b "## Test plan"',
        'gh pr create --title Notes --body="## Risks"',
        'gh pr create --body "Adds notes.\n\nCo-Authored-By: Someone <someone@example.com>"',
        'gh pr edit 12 --body "## Verification"',
        'gh pr edit 12 -b "## Verification"',
        "gh pr create --body " + HEREDOC.format(text="## Verification"),
        "gh pr create --body " + HEREDOC.format(text='Use "both words" here\n## Verification'),
        "gh pr create --body " + HEREDOC.format(text='Odd " quote\n## Verification'),
        "gh pr edit 12 --body " + HEREDOC.format(text="## Verification"),
        "gh pr create --body-file - <<'EOF'\n## Verification\nEOF",
        "gh pr create --body-file body.md",
        "gh pr create -F body.md",
        "gh pr create --body-file=body.md",
        "gh pr edit 12 --body-file body.md",
        "gh pr edit 12 -F body.md",
        "cd docs && gh pr create -F body.md",
    ],
)
def test_a_body_that_fails_R27_is_refused(command, repository):
    repository.configure(["R27"])
    (repository.root / "body.md").write_text("## Verification\n")
    (repository.root / "docs").mkdir()
    (repository.root / "docs" / "body.md").write_text("## Verification\n")
    findings = bash.check(command, repository.root)
    assert [finding.rule for finding in findings] == ["R27"]


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --fill",
        'gh pr create --title "Test notes" --body "Adds notes."',
        "gh pr create --body " + HEREDOC.format(text="Use the test notes."),
        "gh pr create --body-file body.md",
        "gh pr create --body-file missing.md",
        "git commit -m " + HEREDOC.format(text="Co-Authored-By: Someone") + "; gh pr create --fill",
    ],
)
def test_a_body_that_holds_passes(command, repository, monkeypatch):
    monkeypatch.setattr(checkout.Checkout, "branch", lambda self: "dru-1-notes")
    repository.configure(["R27"])
    (repository.root / "body.md").write_text("Adds notes.\n")
    assert bash.check(command, repository.root) == []


def test_a_repository_without_R27_takes_any_body(repository):
    repository.configure(["R14"])
    assert bash.check('gh pr create --body "## Verification"', repository.root) == []
