"""What the Claude Code plugin does at each hook event.

Every event reads the hook input JSON on stdin and answers with the hook output
JSON on stdout. Outside a repository with ``druks-house-rules.toml``, every
event answers nothing.
"""

import json
import pathlib
import subprocess
from collections.abc import Mapping

from . import bash, changes, checkout, config, delta, driver, moves, plans, rules
from .exceptions import ConfigError
from .findings import Finding

EDIT_TOOLS = frozenset({"Edit", "Write", "MultiEdit"})


def run(event: Mapping) -> dict | None:
    name = event.get("hook_event_name")
    tool = event.get("tool_name")
    tool_input = event.get("tool_input") or {}
    if name == "PreToolUse" and tool == "Bash":
        return _permission(bash.check(tool_input.get("command", ""), _branch(event["cwd"])))
    if name == "PreToolUse" and tool == "ExitPlanMode":
        return _permission(plans.check(tool_input.get("plan", "")))
    if name == "PostToolUse" and tool in EDIT_TOOLS:
        return _edit(pathlib.Path(tool_input["file_path"]))
    if name == "Stop" and not event.get("stop_hook_active"):
        return _stop(event["cwd"], pathlib.Path(event["transcript_path"]))
    return None


def _permission(findings: list[Finding]) -> dict | None:
    """Deny the call, or ask the owner when every finding is a rule that asks."""
    if not findings:
        return None
    asked = all(finding.rule in bash.ASKED_RULES for finding in findings)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask" if asked else "deny",
            "permissionDecisionReason": _lines(findings),
        }
    }


def _edit(path: pathlib.Path) -> dict | None:
    repository = _repository(path.parent)
    if not repository:
        return None
    root, settings = repository
    relative = path.resolve().relative_to(root).as_posix()
    change = changes.Change(root, settings, None, None, paths=[relative])
    findings = rules.check(change)
    if not findings:
        return None
    return {"decision": "block", "reason": _lines(findings)}


def _stop(cwd: str, transcript: pathlib.Path) -> dict | None:
    """Hold the change to the rules, the surface and the moves. A change that holds
    goes to the driver, and its phrase is the agent's next turn."""
    repository = _repository(pathlib.Path(cwd))
    if not repository:
        return None
    root, settings = repository
    base = checkout.Checkout(root).default_base()
    if not base:
        return None
    change = changes.Change(root, settings, base, None)
    findings = rules.check(change)
    surface = delta.surface(change)
    applied = moves.check(change)
    if findings or surface or applied:
        reason = [f"druks-house-rules held the change against {base}."]
        if findings:
            reason.append(f"\nFindings; fix each one:\n{_lines(findings)}")
        if surface:
            reason.append(
                "\nSurface the change adds; for each item, name the existing primitive that "
                f"does it, or remove the item:\n{_lines(surface)}\n{delta.ratio(change)}"
            )
        if applied:
            reason.append(
                f"\nMoves from {moves.CATALOG}; apply each one or say why not:\n{_lines(applied)}"
            )
        return {"decision": "block", "reason": "\n".join(reason)}
    pick = driver.pick(root, base, _task(transcript))
    if pick:
        return {"decision": "block", "reason": pick["phrase"]}
    return None


def _task(transcript: pathlib.Path) -> str:
    """What the person asked for in the session, their messages in order."""
    messages = []
    for line in transcript.read_text().splitlines():
        entry = json.loads(line)
        if entry.get("type") == "user" and not entry.get("isMeta") and "toolUseResult" not in entry:
            content = entry["message"]["content"]
            if isinstance(content, str):
                messages.append(content)
            else:
                messages.extend(block["text"] for block in content if block["type"] == "text")
    return "\n\n".join(messages)


def _repository(directory: pathlib.Path) -> tuple[pathlib.Path, config.Config] | None:
    """The checkout root and its configuration, or None outside a configured repository."""
    toplevel = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=directory, capture_output=True, text=True
    )
    if toplevel.returncode:
        return None
    root = pathlib.Path(toplevel.stdout.strip())
    try:
        return root, config.load(root)
    except ConfigError:
        return None


def _branch(cwd: str) -> str | None:
    return checkout.Checkout(pathlib.Path(cwd)).branch()


def _lines(items) -> str:
    return "\n".join(str(item) for item in items)
