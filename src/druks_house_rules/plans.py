"""R1. A plan names, for each thing it adds, the existing primitive and the verified gap.

The ``prior_art`` section holds that. A plan with no such section leaves plan
mode denied. So does a plan whose section does not name a module, class,
setting, column, flag, or dependency the plan adds.
"""

import re

from .findings import Finding

KINDS = r"(?:module|class|setting|column|flag|dependency)"
VERBS = r"(?:new|adds?|added|adding|creates?|introduces?)\s+(?:an?\s+|the\s+)?"
HEADING = re.compile(r"^(?:(#+)\s*|\*\*)\s*prior[ _-]?art\b", re.IGNORECASE | re.MULTILINE)
ANY_HEADING = re.compile(r"^(#+)\s", re.MULTILINE)
KIND_THEN_NAME = re.compile(rf"\b{VERBS}({KINDS})\s+`?([A-Za-z_][\w./-]*)`?", re.IGNORECASE)
NAME_THEN_KIND = re.compile(rf"\b{VERBS}`?([A-Za-z_][\w./-]*)`?\s+({KINDS})\b", re.IGNORECASE)


def check(plan: str) -> list[Finding]:
    heading = HEADING.search(plan)
    if not heading:
        return [
            Finding(
                "plan",
                1,
                "R1",
                "no prior_art section; for each new module, class, setting, column, flag, or "
                "dependency, name the existing primitive and the verified gap",
            )
        ]
    end = _section_end(plan, heading)
    section = plan[heading.end() : end]
    rest = plan[: heading.start()] + plan[end:]
    findings = []
    for kind, name in _additions(rest):
        if name not in section:
            findings.append(
                Finding(
                    "plan",
                    1,
                    "R1",
                    f"prior_art does not name {kind} {name}; name the existing primitive and "
                    "the verified gap, or drop it",
                )
            )
    return findings


def _section_end(plan: str, heading: re.Match) -> int:
    """Where the prior_art section ends: the next heading at its level or above."""
    level = len(heading.group(1) or "")
    for following in ANY_HEADING.finditer(plan, heading.end()):
        if level and len(following.group(1)) <= level:
            return following.start()
    return len(plan)


def _additions(text: str) -> list[tuple[str, str]]:
    additions = [
        (match.group(1).lower(), match.group(2)) for match in KIND_THEN_NAME.finditer(text)
    ]
    additions.extend(
        (match.group(2).lower(), match.group(1)) for match in NAME_THEN_KIND.finditer(text)
    )
    return additions
