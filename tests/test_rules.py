"""Every rule fails its negative fixture and passes its positive fixture, through the CLI."""

import pytest

from druks_house_rules import cli
from tests import conftest

FILE_RULES = ["R14", "rule-3", "rule-2", "rule-1", "R21", "R23", "R5", "R13", "R11", "R16"]


def run(repository: conftest.Repository, *arguments: str, capsys) -> tuple[int, list[str]]:
    code = cli.main(["check", *arguments, str(repository.root)])
    lines = capsys.readouterr().out.splitlines()
    return code, lines


def rules_in(lines: list[str]) -> set[str]:
    return {line.split(" ")[1] for line in lines}


@pytest.mark.parametrize("rule", FILE_RULES)
@pytest.mark.parametrize("verdict", ["pass", "fail"])
def test_file_rule(repository, capsys, rule, verdict):
    repository.add_tree(conftest.FIXTURES / rule / verdict)
    repository.configure([rule])
    repository.commit()
    code, lines = run(repository, capsys=capsys)
    if verdict == "pass":
        assert (code, lines) == (0, [])
    else:
        assert code == 1
        assert rules_in(lines) == {rule}


@pytest.mark.parametrize("verdict", ["pass", "fail"])
def test_R25_mechanism_modules(repository, capsys, verdict):
    repository.configure(["R25"])
    repository.commit()
    repository.add_tree(conftest.FIXTURES / "R25" / verdict)
    repository.commit("DRU-1 -- Add a module")
    code, lines = run(repository, "--base", "main~1", capsys=capsys)
    if verdict == "pass":
        assert (code, lines) == (0, [])
    else:
        assert code == 1
        assert lines == ["druks/mcp/helpers.py:1 R25 helpers.py names a mechanism; name the noun"]


@pytest.mark.parametrize("verdict", ["pass", "fail"])
def test_R28_commits(repository, capsys, verdict):
    repository.configure(["R28"])
    repository.commit()
    message = (conftest.FIXTURES / "R28" / verdict / "message.txt").read_text()
    repository.commit(message)
    code, lines = run(repository, "--base", "main~1", capsys=capsys)
    if verdict == "pass":
        assert (code, lines) == (0, [])
    else:
        assert code == 1
        assert [line.split(" R28 ")[1] for line in lines] == [
            "subject is '<ticket> -- <what the change does>'",
            "subject names a pull request number; GitHub adds it",
            "attribution line: Co-Authored-By: Claude <noreply@anthropic.com>",
        ]


def test_R28_two_commits(repository, capsys):
    repository.configure(["R28"])
    repository.commit()
    repository.commit("DRU-1 -- First")
    repository.commit("DRU-1 -- Second")
    code, lines = run(repository, "--base", "main~2", capsys=capsys)
    assert code == 1
    assert lines[0].endswith(" R28 2 commits above the base; squash them into one")


@pytest.mark.parametrize("verdict", ["pass", "fail"])
def test_R27_pull_request_body(repository, capsys, verdict):
    repository.configure(["R27"])
    repository.commit()
    body = conftest.FIXTURES / "R27" / verdict / "body.md"
    code, lines = run(repository, "--pr-body-file", str(body), capsys=capsys)
    if verdict == "pass":
        assert (code, lines) == (0, [])
    else:
        assert code == 1
        assert lines == [
            "pr-body:3 R27 section '## Verification'; drop it",
            "pr-body:7 R27 section '## Risk'; drop it",
            "pr-body:9 R27 line: Low. Plan: https://linear.app/druks/issue/DRU-912",
        ]


def test_R14_pull_request_text(repository, capsys):
    repository.configure(["R14"])
    repository.commit()
    code, lines = run(repository, "--pr-title", "Show the portal", capsys=capsys)
    assert code == 1
    assert lines == ['pr-title:1 R14 "portal" is on the denylist; remove it']


def test_exceptions_and_exclude(repository, capsys):
    repository.add_tree(conftest.FIXTURES / "rule-2" / "fail")
    repository.add_tree(conftest.FIXTURES / "R14" / "fail")
    repository.configure(
        ["rule-2", "R14"], extra='exclude = ["README.md"]\n[exceptions]\nrule-2 = ["routes.py"]\n'
    )
    repository.commit()
    assert run(repository, capsys=capsys) == (0, [])


def test_base_reads_only_the_changed_files(repository, capsys):
    repository.add_tree(conftest.FIXTURES / "rule-2" / "fail")
    repository.configure(["rule-2"])
    repository.commit()
    (repository.root / "clean.py").write_text("x = 1\n")
    code, lines = run(repository, "--base", "main", capsys=capsys)
    assert (code, lines) == (0, [])


def test_missing_config(repository, capsys):
    repository.commit()
    assert cli.main(["check", str(repository.root)]) == 2
    assert "druks-house-rules.toml" in capsys.readouterr().err
