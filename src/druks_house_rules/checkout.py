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

    def git(self, *args: str, check: bool = True) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.root, check=check, capture_output=True, text=True
        ).stdout

    def tracked_files(self) -> list[str]:
        return self.git("ls-files", "-z").split("\0")[:-1]

    def merge_base(self, base: str) -> str:
        return self.git("merge-base", base, "HEAD").strip()

    def changed_files(self, base_commit: str) -> list[str]:
        """The files the working tree changes or adds against the base commit."""
        changed = self.git("diff", "--name-only", "-z", "--diff-filter=ACMR", base_commit)
        return changed.split("\0")[:-1] + self.untracked_files()

    def added_files(self, base_commit: str) -> list[str]:
        added = self.git("diff", "--name-only", "-z", "--diff-filter=A", base_commit)
        return added.split("\0")[:-1] + self.untracked_files()

    def untracked_files(self) -> list[str]:
        """The files git does not track and does not ignore."""
        return self.git("ls-files", "-z", "--others", "--exclude-standard").split("\0")[:-1]

    def branch(self) -> str | None:
        """The checked-out branch, or None on a detached head."""
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "-q", "HEAD"],
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or None

    def default_base(self) -> str | None:
        """The ref a change is held against: the remote head, ``origin/main``, or ``main``."""
        for ref in ("origin/HEAD", "origin/main", "main"):
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "--verify", "-q", ref],
                cwd=self.root,
                capture_output=True,
                text=True,
            )
            if not result.returncode:
                return result.stdout.strip()
        return None

    def diff(self, base_commit: str) -> str:
        """The working tree against the base commit, untracked files included."""
        text = self.git("diff", base_commit)
        for path in self.untracked_files():
            content = self.read(path)
            if content:
                text += self.git("diff", "--no-index", "--", "/dev/null", path, check=False)
        return text

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
