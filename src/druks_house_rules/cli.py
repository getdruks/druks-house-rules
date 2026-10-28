import argparse
import dataclasses
import json
import pathlib
import sys

from . import changes, config, delta, hooks, moves, rules
from .exceptions import HouseRulesError, MissingConfigError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="druks-house-rules")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="hold the change to the rules; exit 1 on a finding")
    check.add_argument(
        "--base", help="the ref to check the change against; default: the whole checkout"
    )
    check.add_argument("--pr-title", help="the pull request title")
    check.add_argument("--pr-body", help="the pull request body")
    check.add_argument("--json", action="store_true", help="print the findings as a JSON array")
    check.add_argument("root", nargs="?", type=pathlib.Path, default=pathlib.Path("."))
    surface = commands.add_parser(
        "delta", help="print the surface the change adds against its base"
    )
    surface.add_argument("--base", required=True)
    surface.add_argument("root", nargs="?", type=pathlib.Path, default=pathlib.Path("."))
    catalog = commands.add_parser(
        "moves", help="print the moves from the repository's catalog that apply to the change"
    )
    catalog.add_argument("--base", required=True)
    catalog.add_argument("root", nargs="?", type=pathlib.Path, default=pathlib.Path("."))
    commands.add_parser(
        "hook",
        help="answer one Claude Code hook event: the input JSON on stdin, the output on stdout",
    )
    arguments = parser.parse_args(argv)
    try:
        return _run(arguments)
    except MissingConfigError as error:
        print(f"druks-house-rules: {error}", file=sys.stderr)
        return 3
    except HouseRulesError as error:
        print(f"druks-house-rules: {error}", file=sys.stderr)
        return 2


def _run(arguments: argparse.Namespace) -> int:
    if arguments.command == "hook":
        answer = hooks.run(json.load(sys.stdin))
        if answer:
            print(json.dumps(answer))
        return 0
    root = arguments.root.resolve()
    settings = config.load(root)
    if arguments.command == "delta":
        change = changes.Change(root, settings, arguments.base, None)
        for item in delta.surface(change):
            print(item)
        print(delta.ratio(change))
        return 0
    if arguments.command == "moves":
        change = changes.Change(root, settings, arguments.base, None)
        for finding in moves.check(change):
            print(finding)
        return 0
    pull_request = None
    if arguments.pr_body or arguments.pr_title:
        pull_request = changes.PullRequest(
            title=arguments.pr_title or "", body=arguments.pr_body or ""
        )
    change = changes.Change(root, settings, arguments.base, pull_request)
    findings = rules.check(change)
    if arguments.json:
        print(json.dumps([dataclasses.asdict(finding) for finding in findings]))
    else:
        for finding in findings:
            print(finding)
    return 1 if findings else 0
