"""Guard that the type stub mirrors the runtime package ``__init__``.

mypy trusts ``__init__.pyi`` and ignores ``__init__.py``, and ruff only checks a
file against itself, so the stub can silently drift from the real re-exports
without any other check noticing. This test parses both files with the AST and
asserts their ``from ... import ...`` lines and ``__all__`` lists are identical.
"""

import ast
from pathlib import Path

import picmaker


def _imports_and_all(path: Path) -> tuple[dict[str, list[str]], list[str]]:
    """Return ``{module: [names]}`` and the sorted ``__all__`` from a module."""
    tree = ast.parse(path.read_text())
    imports: dict[str, list[str]] = {}
    dunder_all: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports[node.module] = sorted(alias.name for alias in node.names)
        elif (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.List)
            and any(isinstance(t, ast.Name) and t.id == '__all__' for t in node.targets)
        ):
            dunder_all = sorted(
                str(elt.value) for elt in node.value.elts
                if isinstance(elt, ast.Constant)
            )
    return imports, dunder_all


def test_stub_mirrors_init() -> None:
    """``__init__.pyi`` re-exports exactly what ``__init__.py`` does."""
    assert picmaker.__file__ is not None
    pkg = Path(picmaker.__file__).parent
    py_imports, py_all = _imports_and_all(pkg / '__init__.py')
    pyi_imports, pyi_all = _imports_and_all(pkg / '__init__.pyi')

    assert pyi_imports == py_imports, 'stub imports drifted from __init__.py'
    assert pyi_all == py_all, 'stub __all__ drifted from __init__.py'
