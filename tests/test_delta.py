from druks_house_rules import cli
from tests import conftest


def run(repository: conftest.Repository, capsys) -> list[str]:
    assert cli.main(["delta", "--base", "main", str(repository.root)]) == 0
    return capsys.readouterr().out.splitlines()


def test_one_module_one_class_one_setting(repository, capsys):
    repository.add_tree(conftest.FIXTURES / "delta" / "base")
    repository.configure([])
    repository.commit()
    repository.git("checkout", "-q", "-b", "notes")
    repository.add_tree(conftest.FIXTURES / "delta" / "head")
    repository.commit("DRU-1 -- Add notes")
    assert run(repository, capsys) == [
        "backend/druks/models.py:8 class Note",
        "backend/druks/notes.py:1 module backend.druks.notes",
        "backend/druks/settings.py:3 setting Settings.notes_limit",
        "tests/source ratio 0.00 (0 test lines, 6 source lines)",
    ]


def test_every_kind(repository, capsys):
    repository.configure([])
    (repository.root / "pyproject.toml").write_text(
        '[project]\nname = "app"\ndependencies = ["httpx>=0.28"]\n'
    )
    (repository.root / "app.py").write_text("def read(path):\n    return path\n")
    repository.commit()
    repository.git("checkout", "-q", "-b", "change")
    (repository.root / "pyproject.toml").write_text(
        '[project]\nname = "app"\ndependencies = ["httpx>=0.28", "redis>=8"]\n'
    )
    (repository.root / "app.py").write_text(
        "from sqlalchemy.orm import mapped_column\n"
        "\n"
        "\n"
        "class Note:\n"
        "    body: str = mapped_column()\n"
        "\n"
        "\n"
        "def read(path, retries=3):\n"
        "    try:\n"
        "        return path\n"
        "    except OSError:\n"
        "        return retries\n"
    )
    versions = repository.root / "migrations" / "versions"
    versions.mkdir(parents=True)
    (versions / "0002_notes.py").write_text("revision = '0002'\n")
    (repository.root / "tests").mkdir()
    (repository.root / "tests" / "test_app.py").write_text("def test_read():\n    assert read\n")
    repository.commit("DRU-1 -- Add notes")
    assert run(repository, capsys) == [
        "app.py:4 class Note",
        "app.py:5 column Note.body",
        "app.py:8 optional-parameter read(retries=3)",
        "app.py:9 try/except read except OSError",
        "migrations/versions/0002_notes.py:1 migration 0002_notes.py",
        "pyproject.toml:3 dependency redis",
        "tests/source ratio 0.15 (2 test lines, 13 source lines)",
    ]
