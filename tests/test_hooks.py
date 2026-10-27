"""Each hook event answers as Claude Code reads it."""

import io
import json
import os
import pathlib
import stat

import pytest

from druks_house_rules import cli, hooks, moves
from tests import conftest

CATALOG = """# Moves

- bag parameter: a public function takes an `int` beside a `dict[str, Any]`.
- unnamed condition: an `if` with five or more clauses, or a comment inside it.
"""


def event(name: str, root: pathlib.Path, **fields) -> dict:
    return {"hook_event_name": name, "cwd": str(root), **fields}


@pytest.fixture
def druks_repository(repository: conftest.Repository) -> conftest.Repository:
    """A configured repository on a branch above ``main``, with ``origin/HEAD`` set."""
    repository.configure(["rule-2", "R25"])
    repository.add_tree(conftest.FIXTURES / "delta" / "base")
    repository.commit()
    repository.git("remote", "add", "origin", str(repository.root))
    repository.git("fetch", "-q", "origin")
    repository.git("remote", "set-head", "origin", "main")
    repository.git("checkout", "-q", "-b", "notes")
    return repository


@pytest.fixture
def no_claude(monkeypatch):
    """A moves pass that finds no CLI, so it answers nothing."""
    monkeypatch.setattr(moves, "ask", lambda prompt: "")


def test_edit_with_is_none_is_fed_back(druks_repository, no_claude):
    path = druks_repository.root / "routes.py"
    path.write_text("def read(value):\n    if value is None:\n        return 1\n    return 2\n")
    answer = hooks.run(
        event(
            "PostToolUse",
            druks_repository.root,
            tool_name="Write",
            tool_input={"file_path": str(path)},
        )
    )
    assert answer["decision"] == "block"
    assert answer["reason"].startswith("routes.py:2 rule-2 ")


def test_clean_edit_answers_nothing(druks_repository):
    path = druks_repository.root / "routes.py"
    path.write_text("def read(value):\n    if value:\n        return 1\n    return 2\n")
    tool_input = {"file_path": str(path)}
    assert not hooks.run(
        event("PostToolUse", druks_repository.root, tool_name="Edit", tool_input=tool_input)
    )


def test_edit_outside_a_configured_repository_answers_nothing(tmp_path):
    path = tmp_path / "routes.py"
    path.write_text("x = None\n")
    tool_input = {"file_path": str(path)}
    assert not hooks.run(event("PostToolUse", tmp_path, tool_name="Write", tool_input=tool_input))


def test_stop_lists_findings_and_surface_once(druks_repository, no_claude):
    druks_repository.add_tree(conftest.FIXTURES / "delta" / "head")
    (druks_repository.root / "backend" / "druks" / "utils.py").write_text("x = 1\n")
    answer = hooks.run(event("Stop", druks_repository.root, stop_hook_active=False))
    assert answer["decision"] == "block"
    reason = answer["reason"]
    assert reason.startswith("druks-house-rules held the change against origin/main.")
    assert "backend/druks/utils.py:1 R25 utils.py names a mechanism; name the noun" in reason
    assert "backend/druks/notes.py:1 module backend.druks.notes" in reason
    assert "backend/druks/settings.py:3 setting Settings.notes_limit" in reason
    assert "backend/druks/utils.py:1 module backend.druks.utils" in reason
    assert not hooks.run(event("Stop", druks_repository.root, stop_hook_active=True))


def test_stop_with_nothing_added_answers_nothing(druks_repository, no_claude):
    assert not hooks.run(event("Stop", druks_repository.root, stop_hook_active=False))


def test_bash_on_main_is_denied(druks_repository):
    druks_repository.git("checkout", "-q", "main")
    tool_input = {"command": 'git commit -m "DRU-1 -- Add notes"'}
    answer = hooks.run(
        event("PreToolUse", druks_repository.root, tool_name="Bash", tool_input=tool_input)
    )
    assert answer == {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "command:1 R33 commit on main; create a branch and open a pull request"
            ),
        }
    }


def test_exit_plan_mode_without_prior_art_is_denied(druks_repository):
    tool_input = {"plan": "# Notes\n\nAdd a class `Note`.\n"}
    answer = hooks.run(
        event("PreToolUse", druks_repository.root, tool_name="ExitPlanMode", tool_input=tool_input)
    )
    assert answer["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "R1 no prior_art section" in answer["hookSpecificOutput"]["permissionDecisionReason"]


def test_moves_pass_sends_catalog_surface_and_diff(druks_repository, monkeypatch, tmp_path):
    catalog = druks_repository.root / moves.CATALOG
    catalog.parent.mkdir(parents=True)
    catalog.write_text(CATALOG)
    druks_repository.commit("DRU-1 -- Add the catalog")
    druks_repository.add_tree(conftest.FIXTURES / "delta" / "head")
    sent = tmp_path / "prompt.txt"
    fake = tmp_path / "bin" / "claude"
    fake.parent.mkdir()
    answer = {
        "moves": [
            {
                "path": "backend/druks/notes.py",
                "line": 1,
                "move": "bag parameter",
                "why": "int beside dict",
            }
        ]
    }
    fake.write_text(
        f"#!/bin/sh\ncat > {sent}\nprintf '%s' '{json.dumps({'result': json.dumps(answer)})}'\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{fake.parent}{os.pathsep}{os.environ['PATH']}")
    reply = hooks.run(event("Stop", druks_repository.root, stop_hook_active=False))
    assert "backend/druks/notes.py:1 move bag parameter: int beside dict" in reply["reason"]
    prompt = sent.read_text()
    assert "unnamed condition" in prompt
    assert "backend/druks/settings.py:3 setting Settings.notes_limit" in prompt
    assert "+class Note" in prompt


def test_parse_tolerates_a_code_fence():
    assert moves.parse('```json\n{"moves": []}\n```') == []
    assert moves.parse("") == []


def test_merge_asks_the_owner_through_the_hook_command(druks_repository, monkeypatch, capsys):
    tool_input = {"command": "gh pr merge 1"}
    stdin = json.dumps(
        event("PreToolUse", druks_repository.root, tool_name="Bash", tool_input=tool_input)
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    assert cli.main(["hook"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["hookSpecificOutput"]["permissionDecision"] == "ask"
    assert "R35" in printed["hookSpecificOutput"]["permissionDecisionReason"]
