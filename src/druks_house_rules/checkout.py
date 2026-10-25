"""Read-only access to the git checkout under check."""

import dataclasses
import pathlib
import subprocess


@dataclasses.dataclass(frozen=True)
class Commit:
    sha: str
    subject: str
    body: str


class Checkout:
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.root, check=True, capture_output=True, text=True
        ).stdout

    def tracked_files(self) -> list[str]:
        return self.git("ls-files", "-z").split("\0")[:-1]

    def merge_base(self, base: str) -> str:
        return self.git("merge-base", base, "HEAD").strip()

    def changed_files(self, base_commit: str) -> list[str]:
        """The files the working tree changes or adds against the base commit."""
        return self.git("diff", "--name-only", "-z", "--diff-filter=ACMR", base_commit).split("\0")[
            :-1
        ]

    def added_files(self, base_commit: str) -> list[str]:
        return self.git("diff", "--name-only", "-z", "--diff-filter=A", base_commit).split("\0")[
            :-1
        ]

    def added_lines(self, base_commit: str) -> dict[str, int]:
        """Lines the working tree adds per file against the base commit."""
        added = {}
        for row in self.git("diff", "--numstat", base_commit).splitlines():
            count, _, path = row.split("\t", 2)
            if count != "-":
                added[path] = int(count)
        return added

    def commits(self, base_commit: str) -> list[Commit]:
        """The commits above the base commit, oldest first."""
        commits = []
        log = self.git("log", "--reverse", "--format=%H%x00%s%x00%b%x01", f"{base_commit}..HEAD")
        for record in log.split("\x01"):
            if record.strip():
                sha, subject, body = record.lstrip("\n").split("\0", 2)
                commits.append(Commit(sha=sha, subject=subject, body=body))
        return commits

    def file_at(self, commit: str, path: str) -> str | None:
        """The file's text at the commit, or None when the commit does not hold the file."""
        result = subprocess.run(
            ["git", "show", f"{commit}:{path}"], cwd=self.root, capture_output=True, text=True
        )
        if result.returncode:
            return None
        return result.stdout

    def read(self, path: str) -> str | None:
        """The file's text in the working tree, or None when it is not text."""
        try:
            return (self.root / path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None
