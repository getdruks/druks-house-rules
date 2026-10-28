"""The app checks each head once and posts the findings as a check run."""

import json
import subprocess
from unittest import mock

from druks.core.services import Github
from druks.testing import run_workflow

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
