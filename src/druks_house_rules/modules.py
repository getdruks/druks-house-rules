"""R25. A module is named for the domain noun it holds, not for its mechanism."""

import pathlib

from druks_house_rules import changes
from druks_house_rules.findings import Finding

MECHANISM_NAMES = frozenset({"deps.py", "helpers.py", "utils.py", "common.py", "misc.py"})


def check(change: changes.Change) -> list[Finding]:
    return [
        Finding(
            path, 1, "R25", f"{pathlib.PurePosixPath(path).name} names a mechanism; name the noun"
        )
        for path in change.added_files
        if pathlib.PurePosixPath(path).name in MECHANISM_NAMES
    ]
