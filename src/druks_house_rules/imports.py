"""R16. Author-surface modules never import an app; apps import only the public surface."""

import importlib
import sys

import grimp

from druks_house_rules import changes
from druks_house_rules.findings import Finding


def check(change: changes.Change) -> list[Finding]:
    direction = change.config.import_direction
    if not direction:
        return []
    source_root = str(change.root / direction.root)
    sys.path.insert(0, source_root)
    importlib.invalidate_caches()
    try:
        graph = grimp.build_graph(direction.package, cache_dir=None)
    finally:
        sys.path.remove(source_root)
    findings = []
    children = graph.find_children(direction.package)
    internal = [
        child
        for child in children
        if not _within(child, direction.public) and not _within(child, direction.apps)
    ]
    contracts = [
        (direction.author_surface, direction.apps, "an author-surface module imports an app"),
        (direction.apps, tuple(internal), "an app imports an internal module"),
    ]
    for sources, forbidden, message in contracts:
        for importer in sorted(_modules_within(graph, sources)):
            for imported in sorted(graph.find_modules_directly_imported_by(importer)):
                if not _within(imported, forbidden) or direction.ignores(importer, imported):
                    continue
                for detail in graph.get_import_details(importer=importer, imported=imported):
                    findings.append(
                        Finding(
                            _path(change, importer),
                            detail["line_number"],
                            "R16",
                            f"{message}: {imported}",
                        )
                    )
    return findings


def _modules_within(graph: grimp.ImportGraph, roots: tuple[str, ...]) -> set[str]:
    modules = set()
    for root in roots:
        if root in graph.modules:
            modules.add(root)
            modules |= graph.find_descendants(root)
    return modules


def _within(module: str, roots: tuple[str, ...]) -> bool:
    return any(module == root or module.startswith(root + ".") for root in roots)


def _path(change: changes.Change, module: str) -> str:
    direction = change.config.import_direction
    base = f"{direction.root}/{module.replace('.', '/')}"
    if (change.root / f"{base}.py").is_file():
        return f"{base}.py"
    return f"{base}/__init__.py"
