"""The change under check: a working tree against a base, or a whole checkout."""

import ast
import dataclasses
import functools
import pathlib

from druks_house_rules import checkout
from druks_house_rules import config


@dataclasses.dataclass(frozen=True)
class PullRequest:
    title: str
    body: str


@dataclasses.dataclass(frozen=True)
class Module:
    path: str
    source: str
    tree: ast.Module

    @property
    def lines(self) -> list[str]:
        return self.source.splitlines()


class Change:
    """What the rules read.

    With a base, the files are the ones the working tree changes against the
    merge base and the commits are the ones above it. Without a base, the files
    are every tracked file and there are no commits.
    """

    def __init__(
        self,
        root: pathlib.Path,
        settings: config.Config,
        base: str | None,
        pull_request: PullRequest | None,
    ) -> None:
        self.root = root
        self.config = settings
        self.checkout = checkout.Checkout(root)
        self.base_commit = self.checkout.merge_base(base) if base else None
        self.pull_request = pull_request

    @functools.cached_property
    def files(self) -> list[str]:
        if self.base_commit:
            files = self.checkout.changed_files(self.base_commit)
        else:
            files = self.checkout.tracked_files()
        return [path for path in files if not self.config.excluded(path)]

    @functools.cached_property
    def added_files(self) -> list[str]:
        if self.base_commit:
            files = self.checkout.added_files(self.base_commit)
        else:
            files = self.checkout.tracked_files()
        return [path for path in files if not self.config.excluded(path)]

    @functools.cached_property
    def commits(self) -> list[checkout.Commit]:
        if self.base_commit:
            return self.checkout.commits(self.base_commit)
        return []

    @functools.cached_property
    def modules(self) -> list[Module]:
        """The changed Python files that parse. ruff reports the ones that do not."""
        modules = []
        for path in self.files:
            if not path.endswith(".py"):
                continue
            source = self.checkout.read(path)
            if not source:
                continue
            try:
                tree = ast.parse(source, filename=path)
            except SyntaxError:
                continue
            modules.append(Module(path=path, source=source, tree=tree))
        return modules

    def texts(self):
        """Yield (path, text) for every changed file that is text."""
        for path in self.files:
            text = self.checkout.read(path)
            if text:
                yield path, text
