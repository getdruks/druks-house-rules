"""The ``druks-house-rules.toml`` a repository keeps in its root."""

import dataclasses
import pathlib
import re
import tomllib
from collections.abc import Mapping

from druks_house_rules import globs
from druks_house_rules.exceptions import ConfigError

FILENAME = "druks-house-rules.toml"

RULES = {
    "R14": "denylist",
    "R28": "commits",
    "R27": "pull request body",
    "rule-3": "guards",
    "rule-2": "truthiness",
    "rule-1": "bare return",
    "R21": "module imports",
    "R23": "function-level imports",
    "R5": "catches",
    "R13": "sync code",
    "R11": "steps",
    "R25": "mechanism modules",
    "R16": "import direction",
}


@dataclasses.dataclass(frozen=True)
class ImportDirection:
    """What R16 holds a root package to.

    ``root`` is the directory, relative to the checkout, that holds ``package``.
    Author-surface modules never import an app package. App packages import
    only the public modules. ``ignore_imports`` lists ``importer -> imported``
    module globs that the contract tolerates.
    """

    root: str
    package: str
    author_surface: tuple[str, ...]
    public: tuple[str, ...]
    apps: tuple[str, ...]
    ignore_imports: tuple[tuple[re.Pattern[str], re.Pattern[str]], ...]

    def ignores(self, importer: str, imported: str) -> bool:
        return any(
            source.match(importer) and target.match(imported)
            for source, target in self.ignore_imports
        )


@dataclasses.dataclass(frozen=True)
class Config:
    rules: tuple[str, ...]
    exclude: tuple[re.Pattern[str], ...]
    exceptions: Mapping[str, tuple[re.Pattern[str], ...]]
    denylist: tuple[str, ...]
    import_modules: tuple[str, ...]
    import_direction: ImportDirection | None

    def excluded(self, path: str) -> bool:
        return path == FILENAME or any(pattern.match(path) for pattern in self.exclude)

    def excepted(self, rule: str, path: str) -> bool:
        return any(pattern.match(path) for pattern in self.exceptions.get(rule, ()))


def load(root: pathlib.Path) -> Config:
    path = root / FILENAME
    if not path.is_file():
        raise ConfigError(f"{path} is missing. Add it to the repository root.")
    table = tomllib.loads(path.read_text())
    _only_keys(table, {"rules", "exclude", "exceptions", "R14", "R21", "R16"}, FILENAME)
    rules = tuple(table.get("rules", RULES))
    for rule in rules:
        if rule not in RULES:
            raise ConfigError(f"{FILENAME}: unknown rule {rule!r}. Use one of {sorted(RULES)}.")
    exceptions = {}
    for rule, paths in table.get("exceptions", {}).items():
        if rule not in RULES:
            raise ConfigError(f"{FILENAME}: [exceptions] names unknown rule {rule!r}.")
        exceptions[rule] = tuple(globs.compile_glob(glob) for glob in paths)
    return Config(
        rules=rules,
        exclude=tuple(globs.compile_glob(glob) for glob in table.get("exclude", [])),
        exceptions=exceptions,
        denylist=_denylist(table, rules),
        import_modules=("typing", *table.get("R21", {}).get("modules", [])),
        import_direction=_import_direction(table, rules),
    )


def _denylist(table: Mapping, rules: tuple[str, ...]) -> tuple[str, ...]:
    if "R14" not in rules:
        return ()
    words = table.get("R14", {}).get("words")
    if not words:
        raise ConfigError(f"{FILENAME}: R14 runs but [R14] has no words. Add words = [...].")
    return tuple(words)


def _import_direction(table: Mapping, rules: tuple[str, ...]) -> ImportDirection | None:
    if "R16" not in rules:
        return None
    section = table.get("R16")
    if not section:
        raise ConfigError(f"{FILENAME}: R16 runs but [R16] is missing. Add it or drop R16.")
    _only_keys(
        section,
        {"root", "package", "author_surface", "public", "apps", "ignore_imports"},
        "[R16]",
    )
    for key in ("root", "package", "author_surface", "public", "apps"):
        if key not in section:
            raise ConfigError(f"{FILENAME}: [R16] needs {key}.")
    ignore_imports = []
    for entry in section.get("ignore_imports", []):
        importer, arrow, imported = entry.partition(" -> ")
        if not arrow:
            raise ConfigError(f"{FILENAME}: [R16] ignore_imports entry {entry!r} needs ' -> '.")
        ignore_imports.append(
            (globs.compile_glob(importer, "."), globs.compile_glob(imported, "."))
        )
    return ImportDirection(
        root=section["root"],
        package=section["package"],
        author_surface=tuple(section["author_surface"]),
        public=tuple(section["public"]),
        apps=tuple(section["apps"]),
        ignore_imports=tuple(ignore_imports),
    )


def _only_keys(table: Mapping, allowed: set[str], where: str) -> None:
    unknown = set(table) - allowed
    if unknown:
        raise ConfigError(f"{FILENAME}: {where} has unknown keys {sorted(unknown)}.")
