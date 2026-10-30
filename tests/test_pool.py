"""The pool: every entry carries the five fields, a known theme, a count, and its
position as its id."""

import importlib.resources

import pytest
import yaml

THEMES = {
    "overengineering",
    "primitives",
    "naming",
    "wrong layer",
    "steps",
    "tests",
    "imports",
    "narration",
    "scope",
}
FIELDS = {"id", "phrase", "theme", "situation", "count"}


def load() -> list[dict]:
    text = importlib.resources.files("druks_house_rules").joinpath("templates/pool.yml").read_text()
    return yaml.safe_load(text)


def check(entry: dict) -> None:
    assert set(entry) == FIELDS, f"fields {sorted(entry)}"
    assert entry["theme"] in THEMES, f"unknown theme {entry['theme']!r}"
    assert entry["phrase"].strip(), "empty phrase"
    assert entry["situation"].strip(), "empty situation"
    assert entry["count"] >= 1, f"count {entry['count']!r}"


def test_every_entry_is_well_formed():
    pool = load()
    assert [entry["id"] for entry in pool] == list(range(1, len(pool) + 1))
    for entry in pool:
        check(entry)


def test_every_theme_has_entries():
    assert {entry["theme"] for entry in load()} == THEMES


@pytest.mark.parametrize(
    "broken",
    [
        {"id": 1, "phrase": "x", "theme": "naming", "count": 1},
        {"id": 1, "phrase": "x", "theme": "style", "situation": "y", "count": 1},
        {"id": 1, "phrase": "x", "theme": "naming", "situation": "y", "count": 0},
        {"id": 1, "phrase": "x", "theme": "naming", "situation": "y", "count": 1, "source": "s"},
    ],
)
def test_check_fails_on_a_broken_entry(broken):
    with pytest.raises(AssertionError):
        check(broken)
