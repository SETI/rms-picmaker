"""Regenerate every binary test fixture by importing and running each
sibling `<name>_recipe.py` module.

Each recipe writes its output into the sibling `tests/fixtures/` directory
(via `Path(__file__).parent.parent / 'fixtures' / '<name>.<ext>'`); this
script does nothing with the output path itself — it just imports each
recipe and calls its `main()`.

Run from the venv:
    python tests/fixture_recipes/regenerate_all.py
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).parent


def run(recipe_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(recipe_path.stem, recipe_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load recipe: {recipe_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()
    print(f'  ok: {recipe_path.name}')


def main() -> int:
    recipes = sorted(HERE.glob('*_recipe.py'))
    if not recipes:
        print('no recipes found', file=sys.stderr)
        return 1
    for recipe in recipes:
        run(recipe)
    return 0


if __name__ == '__main__':
    sys.exit(main())
