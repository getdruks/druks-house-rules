import argparse
import pathlib
import sys

from druks_house_rules import changes
from druks_house_rules import config
from druks_house_rules import delta
from druks_house_rules import rules
from druks_house_rules.exceptions import HouseRulesError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="druks-house-rules")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="hold the change to the rules; exit 1 on a finding")
    check.add_argument(
        "--base", help="the ref to check the change against; default: the whole checkout"
    )
    check.add_argument("--pr-title", help="the pull request title")
    check.add_argument(
        "--pr-body-file", type=pathlib.Path, help="a file holding the pull request body"
    )
    check.add_argument("root", nargs="?", type=pathlib.Path, default=pathlib.Path("."))
    surface = commands.add_parser(
        "delta", help="print the surface the change adds against its base"
    )
    surface.add_argument("--base", required=True)
    surface.add_argument("root", nargs="?", type=pathlib.Path, default=pathlib.Path("."))
    arguments = parser.parse_args(argv)
    try:
        return _run(arguments)
    except HouseRulesError as error:
        print(f"druks-house-rules: {error}", file=sys.stderr)
        return 2


def _run(arguments: argparse.Namespace) -> int:
    root = arguments.root.resolve()
    settings = config.load(root)
    if arguments.command == "delta":
        change = changes.Change(root, settings, arguments.base, None)
        for item in delta.surface(change):
            print(item)
        print(delta.ratio(change))
        return 0
    pull_request = None
    if arguments.pr_body_file or arguments.pr_title:
        body = arguments.pr_body_file.read_text() if arguments.pr_body_file else ""
        pull_request = changes.PullRequest(title=arguments.pr_title or "", body=body)
    change = changes.Change(root, settings, arguments.base, pull_request)
    findings = rules.check(change)
    for finding in findings:
        print(finding)
    return 1 if findings else 0
