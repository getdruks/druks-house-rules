import pathlib
import shutil
import subprocess

import pytest

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

CONFIG = """
rules: {rules}
{extra}

R16:
  root: "."
  package: pkg
  author_surface: [pkg.workflows, pkg.db]
  public: [pkg.workflows, pkg.db]
  apps: [pkg.contrib]
"""


class Repository:
    """A git repository in a temporary directory, built from fixture trees."""

    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        root.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "tests@example.com")
        self.git("config", "user.name", "tests")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.root, check=True, capture_output=True, text=True
        ).stdout

    def configure(self, rules: list[str], extra: str = "") -> None:
        """Write the configuration; ``extra`` is YAML placed before the R16 key."""
        rules_yaml = "[" + ", ".join(f'"{rule}"' for rule in rules) + "]"
        (self.root / ".druks" / "house_rules").mkdir(parents=True, exist_ok=True)
        (self.root / ".druks" / "house_rules" / "config.yml").write_text(
            CONFIG.format(rules=rules_yaml, extra=extra)
        )

    def add_tree(self, fixture: pathlib.Path) -> None:
        shutil.copytree(fixture, self.root, dirs_exist_ok=True)

    def commit(self, message: str = "base") -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)


@pytest.fixture
def repository(tmp_path: pathlib.Path) -> Repository:
    return Repository(tmp_path / "repo")
