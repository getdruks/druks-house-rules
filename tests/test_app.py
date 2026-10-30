"""The app checks each head once, posts the findings as a check run, and picks one phrase
from the pool for a change."""

import json
import subprocess
from unittest import mock

import pytest
from druks.core.services import Github
from druks.prompts import render_prompt
from druks.testing import run_workflow
from pydantic import ValidationError

from druks_house_rules import app, driver, hooks
from druks_house_rules.contracts import Pick
from druks_house_rules.models import Check
from druks_house_rules.workflows import HouseRules

HEAD = {
    "repo": "acme/widgets",
    "pr_number": 7,
    "head_sha": "0f3a2c1d9e7b",
    "base_branch": "main",
    "title": "DRU-1 -- Add notes",
    "body": "",
}


async def test_dispatch_starts_one_run_per_head_title_and_body(druks_db, monkeypatch):
    start = mock.AsyncMock(return_value="run-1")
    monkeypatch.setattr(HouseRules, "start", staticmethod(start))

    await HouseRules.dispatch(**HEAD)
    await (await Check.get(pr_number=7)).conclude("success")
    await HouseRules.dispatch(**HEAD)
    await HouseRules.dispatch(**{**HEAD, "title": "DRU-1 -- Add notes and gists"})

    assert start.await_count == 2
    assert [check.title for check in await Check.all()] == [
        "DRU-1 -- Add notes",
        "DRU-1 -- Add notes and gists",
    ]


async def test_run_posts_one_annotation_per_finding(druks_db, monkeypatch):
    findings = [
        {"path": "README.md", "line": 4, "rule": "R14", "message": "link to a Notion page"},
        {
            "path": "commit:0f3a2c1d",
            "line": 1,
            "rule": "R28",
            "message": "2 commits above base",
        },
    ]
    exec = mock.AsyncMock(return_value=subprocess.CompletedProcess([], 1, json.dumps(findings), ""))
    monkeypatch.setattr(HouseRules, "exec", exec)
    github = mock.AsyncMock()
    monkeypatch.setattr(Github, "get_client", mock.AsyncMock(return_value=github))
    check = await Check.create(**HEAD)

    await run_workflow(HouseRules, subject=check)

    exec.assert_awaited_once_with(
        [
            "druks-house-rules",
            "check",
            "--json",
            "--base",
            "origin/main",
            "--pr-title",
            "DRU-1 -- Add notes",
            "--pr-body",
            "",
        ]
    )
    github.post_check_run.assert_awaited_once_with(
        "acme/widgets",
        head_sha="0f3a2c1d9e7b",
        name="druks-house-rules",
        status="completed",
        conclusion="failure",
        title="2 findings",
        summary=(
            "```\n"
            "README.md:4 R14 link to a Notion page\n"
            "commit:0f3a2c1d:1 R28 2 commits above base\n"
            "```"
        ),
        annotations=[
            {
                "path": "README.md",
                "start_line": 4,
                "end_line": 4,
                "annotation_level": "failure",
                "title": "R14",
                "message": "link to a Notion page",
            },
            {
                "path": "commit:0f3a2c1d",
                "start_line": 1,
                "end_line": 1,
                "annotation_level": "failure",
                "title": "R28",
                "message": "2 commits above base",
            },
        ],
    )
    assert check.conclusion == "failure"


def test_pick_carries_the_phrase_verbatim_and_records_a_hit():
    phrase = driver.POOL[11]["phrase"]
    pick = Pick(entry=12, where="models.py adds a column for one edge case.")

    assert (pick.phrase, pick.to_event()) == (
        phrase,
        {"topic": "rule.hit", "summary": f"12: {phrase}"},
    )
    assert Pick(entry=None, where="").to_event() == {"topic": "rule.hit", "summary": "none"}
    with pytest.raises(ValidationError):
        Pick(entry=9999, where="")


async def test_driver_prompt_is_the_cli_prompt():
    rendered = await render_prompt("house_rules/driver.md", task="Add notes.", diff="+x = 1")

    assert rendered == driver.ENVIRONMENT.get_template("house_rules/driver.md").render(
        task="Add notes.", diff="+x = 1"
    )


@pytest.mark.parametrize(("entry", "phrase"), [(12, driver.POOL[11]["phrase"]), (None, None)])
async def test_the_implementer_hears_the_picked_phrase(monkeypatch, entry, phrase):
    pick = mock.AsyncMock(return_value=Pick(entry=entry, where=""))
    monkeypatch.setattr(app.HouseRules, "driver", pick)
    workspace = mock.Mock(get_diff=mock.AsyncMock(return_value="+x = 1"))

    assert await hooks.phrase(prompt="Add notes.", workspace=workspace) == phrase
    pick.assert_awaited_once_with(diff="+x = 1", task="Add notes.")
    assert hooks.implementer.id == "software_factory.implement"
