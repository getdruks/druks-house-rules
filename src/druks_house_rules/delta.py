"""The surface a branch adds against its base.

New modules, classes, public functions, settings keys, columns, migrations,
dependencies, ``try/except`` blocks, and optional parameters, plus the ratio
of added test lines to added source lines. Each item is a question for the
author: which existing primitive does this, or why is it needed.
"""

import ast
import collections
import dataclasses
import pathlib
import re
import tomllib

from . import changes

COLUMN_CALLS = frozenset({"mapped_column", "Column"})
TRY = "try/except"
DEPENDENCY_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")
MIGRATION = re.compile(r"(^|/)migrations/versions/[^/]+\.py$")
TEST_PATH = re.compile(r"(^|/)tests?/|(^|/)test_[^/]*\.py$|_test\.py$")


@dataclasses.dataclass(frozen=True, order=True)
class Item:
    path: str
    line: int
    kind: str
    name: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line} {self.kind} {self.name}"


def surface(change: changes.Change) -> list[Item]:
    items = []
    for path in change.added_files:
        if TEST_PATH.search(path):
            continue
        if path.endswith(".py") and not MIGRATION.search(path):
            items.append(Item(path, 1, "module", _module_name(path)))
        if MIGRATION.search(path):
            items.append(Item(path, 1, "migration", pathlib.PurePosixPath(path).name))
    for module in change.modules:
        if TEST_PATH.search(module.path):
            continue
        before = change.checkout.file_at(change.base_commit, module.path)
        for line, kind, name in _added(module.tree, ast.parse(before or "")):
            items.append(Item(module.path, line, kind, name))
    items.extend(_dependencies(change))
    return sorted(items)


def ratio(change: changes.Change) -> str:
    """One line: added test lines against added source lines, Python only."""
    tests, source = _added_lines(change)
    value = f"{tests / source:.2f}" if source else "n/a"
    return f"tests/source ratio {value} ({tests} test lines, {source} source lines)"


def is_test_heavy(change: changes.Change) -> bool:
    """Whether the added tests pass 3 lines per source line plus 30. The flat 30 lets a
    small fix keep its one test, which a plain ratio would flag."""
    tests, source = _added_lines(change)
    return source > 0 and tests > 3 * source + 30


def _added_lines(change: changes.Change) -> tuple[int, int]:
    tests = source = 0
    for path, count in change.checkout.added_lines(change.base_commit).items():
        if not path.endswith(".py") or change.config.excluded(path):
            continue
        if TEST_PATH.search(path):
            tests += count
        else:
            source += count
    return tests, source


def _module_name(path: str) -> str:
    parts = pathlib.PurePosixPath(path).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _added(tree: ast.Module, base: ast.Module) -> list[tuple[int, str, str]]:
    """The items the tree holds beyond the base, one per occurrence. A ``try`` whose
    handlers changed is the same ``try``, so it pairs with the one its function lost."""
    unmatched = collections.Counter((kind, name) for _, kind, name in _walk_with_nodes(base, ""))
    added = []
    for node, kind, name in _walk_with_nodes(tree, ""):
        if unmatched[kind, name]:
            unmatched[kind, name] -= 1
        else:
            added.append((node.lineno, kind, name))
    edited = collections.Counter(
        _function(name) for kind, name in unmatched.elements() if kind == TRY
    )
    kept = []
    for line, kind, name in added:
        if kind == TRY and edited[_function(name)]:
            edited[_function(name)] -= 1
        else:
            kept.append((line, kind, name))
    return kept


def _function(try_name: str) -> str:
    return try_name.partition(" except ")[0]


def _walk_with_nodes(tree: ast.AST, prefix: str):
    """Yield (node, kind, name) for every surface item under the tree."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            qualname = f"{prefix}{node.name}"
            yield node, "class", qualname
            yield from _fields(node, qualname)
            yield from _walk_with_nodes(node, f"{qualname}.")
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            qualname = f"{prefix}{node.name}"
            if not node.name.startswith("_"):
                yield node, "function", qualname
            yield from _optional_parameters(node, qualname)
            yield from _walk_with_nodes(node, f"{qualname}.")
        elif isinstance(node, ast.Try):
            if node.handlers:
                handlers = ", ".join(
                    ast.unparse(handler.type) if handler.type else "bare"
                    for handler in node.handlers
                )
                yield node, TRY, f"{prefix.rstrip('.') or '<module>'} except {handlers}"
            yield from _walk_with_nodes(node, prefix)
        else:
            yield from _walk_with_nodes(node, prefix)


def _fields(node: ast.ClassDef, qualname: str):
    for statement in node.body:
        if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.target, ast.Name):
            continue
        field = statement.target.id
        if node.name.endswith("Settings"):
            yield statement, "setting", f"{qualname}.{field}"
        if isinstance(statement.value, ast.Call) and _call_name(statement.value) in COLUMN_CALLS:
            yield statement, "column", f"{qualname}.{field}"


def _optional_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef, qualname: str):
    arguments = node.args
    positional = arguments.posonlyargs + arguments.args
    for argument, default in zip(
        positional[len(positional) - len(arguments.defaults) :], arguments.defaults, strict=True
    ):
        yield argument, "optional-parameter", f"{qualname}({argument.arg}={ast.unparse(default)})"
    for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True):
        if default:
            yield (
                argument,
                "optional-parameter",
                f"{qualname}({argument.arg}={ast.unparse(default)})",
            )


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _dependencies(change: changes.Change) -> list[Item]:
    if "pyproject.toml" not in change.files:
        return []
    text = change.checkout.read("pyproject.toml")
    before = change.checkout.file_at(change.base_commit, "pyproject.toml") or ""
    base_names = {_dependency_name(entry) for entry in _dependency_entries(before)}
    items = []
    lines = text.splitlines()
    for entry in _dependency_entries(text):
        name = _dependency_name(entry)
        if name in base_names:
            continue
        line = next((number for number, row in enumerate(lines, start=1) if entry in row), 1)
        items.append(Item("pyproject.toml", line, "dependency", name))
    return items


def _dependency_entries(text: str) -> list[str]:
    table = tomllib.loads(text)
    project = table.get("project", {})
    entries = list(project.get("dependencies", []))
    for group in project.get("optional-dependencies", {}).values():
        entries.extend(group)
    for group in table.get("dependency-groups", {}).values():
        entries.extend(entry for entry in group if not isinstance(entry, dict))
    return entries


def _dependency_name(entry: str) -> str:
    match = DEPENDENCY_NAME.match(entry)
    return match.group(0).lower() if match else entry
