"""The drive command prints the picked phrase verbatim from the pool, or nothing."""

import json

import pytest

from druks_house_rules import cli, driver, moves
from tests import conftest


@pytest.fixture
def branch(repository: conftest.Repository) -> conftest.Repository:
    repository.add_tree(conftest.FIXTURES / "delta" / "base")
    repository.commit()
    repository.git("checkout", "-q", "-b", "notes")
    (repository.root / "notes.py").write_text("def read(value):\n    return value\n")
    (repository.root / "task.md").write_text("Add a notes module.")
    return repository


@pytest.mark.parametrize(
    ("answer", "printed"),
    [
        (
            json.dumps({"entry": 3, "where": "notes.py adds read beside an existing reader."}),
            f"{driver.POOL[2]['phrase']}\nnotes.py adds read beside an existing reader.\n",
        ),
        (json.dumps({"entry": None, "where": ""}), ""),
        ("", ""),
    ],
)
def test_drive_prints_the_pick(branch, monkeypatch, capsys, answer, printed):
    prompts = []

    def ask(prompt: str) -> str:
        prompts.append(prompt)
        return answer

    monkeypatch.setattr(moves, "ask", ask)

    code = cli.main(
        ["phrase", "--base", "main", "--task-file", str(branch.root / "task.md"), str(branch.root)]
    )

    assert (code, capsys.readouterr().out) == (0, printed)
    assert "Add a notes module." in prompts[0] and "+def read(value):" in prompts[0]
    assert f"- id: {len(driver.POOL)}\n" in prompts[0] and driver.POOL[-1]["phrase"] in prompts[0]


def test_drive_refuses_an_entry_the_pool_does_not_hold(branch, monkeypatch, capsys):
    monkeypatch.setattr(moves, "ask", lambda prompt: json.dumps({"entry": 9999, "where": "x"}))

    code = cli.main(
        ["phrase", "--base", "main", "--task-file", str(branch.root / "task.md"), str(branch.root)]
    )

    assert code == 2
    assert "not entry 9999" in capsys.readouterr().err
