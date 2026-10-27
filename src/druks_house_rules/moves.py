"""The moves from the repository's catalog that apply to a change.

The catalog is ``.druks/software_factory/review.md``. A small model reads the
catalog, the surface the change adds, and the diff, and names the moves whose
tell is in an added line. The model runs through the Claude Code CLI in print
mode, with hooks and tools off.
"""

import json
import shutil
import subprocess
import sys

from . import changes, delta
from .findings import Finding

CATALOG = ".druks/software_factory/review.md"
MODEL = "haiku"
PROMPT = """You hold one change to a catalog of named moves.

For each move in the catalog, the catalog gives its tell. Read the diff. Name a
move only when its tell is in a line the diff adds. Give the path and the line
number in the new file. One entry per place. An empty list means no move applies.

Answer with this JSON and nothing else:
{{"moves": [{{"path": "<path>", "line": <line>, "move": "<name as the catalog writes it>",
"why": "<one sentence>"}}]}}

# Catalog

{catalog}

# Surface the change adds

{surface}

# Diff

{diff}
"""


def check(change: changes.Change) -> list[Finding]:
    if not (change.root / CATALOG).is_file() or not change.base_commit:
        return []
    prompt = PROMPT.format(
        catalog=change.checkout.read(CATALOG),
        surface="\n".join(str(item) for item in delta.surface(change)) or "nothing",
        diff=change.checkout.diff(change.base_commit) or "nothing",
    )
    answer = ask(prompt)
    return [
        Finding(move["path"], int(move["line"]), "move", f"{move['move']}: {move['why']}")
        for move in parse(answer)
    ]


def ask(prompt: str) -> str:
    """The model's answer to the prompt, or an empty string when the CLI cannot run."""
    binary = shutil.which("claude")
    if not binary:
        print(
            "druks-house-rules: claude is not on PATH; the moves pass is skipped", file=sys.stderr
        )
        return ""
    result = subprocess.run(
        [
            binary,
            "-p",
            "--bare",
            "--model",
            MODEL,
            "--tools",
            "",
            "--no-session-persistence",
            "--output-format",
            "json",
        ],
        input=prompt,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        print(f"druks-house-rules: claude failed: {detail}", file=sys.stderr)
        return ""
    envelope = json.loads(result.stdout)
    if envelope.get("is_error"):
        print(f"druks-house-rules: claude failed: {envelope.get('result')}", file=sys.stderr)
        return ""
    return envelope["result"]


def parse(answer: str) -> list[dict]:
    """The moves in the model's answer, tolerant of a code fence around the JSON."""
    text = answer.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    if not text:
        return []
    return json.loads(text)["moves"]
