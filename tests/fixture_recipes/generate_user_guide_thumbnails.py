"""Generate the User Guide example thumbnails.

These thumbnails illustrate sections 6-9 of ``docs/user_guide.rst``
(supported instruments, output formats, enhancement controls, geometry
controls). They live under ``docs/_static/user_guide/`` and are committed
so a Sphinx build does not require running the test fixtures.

Run from the repo root inside the project venv:

    python tests/fixture_recipes/generate_user_guide_thumbnails.py

Each thumbnail is a one-shot invocation of
:func:`picmaker.pipeline.images_to_pics` against the synthetic fixtures
under ``tests/fixtures/`` produced by the other recipe scripts; nothing
in this generator is bespoke to a real PDS file.

Failures for a given combo are logged and skipped rather than aborting
the run so the bulk of the gallery still regenerates if one instrument
fixture goes missing.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from picmaker.pipeline import images_to_pics

HERE = Path(__file__).parent
FIXTURES = HERE.parent / 'fixtures'
OUT_DIR = HERE.parent.parent / 'docs' / '_static' / 'user_guide'

INSTRUMENT_GALLERY: list[tuple[str, str, dict[str, Any], str]] = [
    # (output_slug, fixture, kwargs, extension)
    ('cassini_iss_tint', 'cassini_iss.vic', {'tint': True}, 'jpg'),
    ('voyager_iss_tint', 'voyager_iss.vic', {'tint': True}, 'jpg'),
    ('galileo_ssi_tint_a', 'galileo_ssi_a.vic', {'tint': True}, 'jpg'),
    ('galileo_ssi_tint_b', 'galileo_ssi_b.vic', {'tint': True}, 'jpg'),
    ('hst_wfc3_tint', 'hst_wfc3.fits', {'tint': True}, 'jpg'),
    ('hst_acs_tint', 'hst_acs.fits', {'tint': True}, 'jpg'),
    ('hst_wfpc2_tint', 'hst_wfpc2.fits', {'tint': True}, 'jpg'),
    ('nh_mvic_tint', 'nh_mvic.fits', {'tint': True}, 'jpg'),
]

OUTPUT_FORMAT_GALLERY: list[tuple[str, str, dict[str, Any], str]] = [
    ('output_jpg', 'cassini_iss.vic', {'quality': 75}, 'jpg'),
    ('output_png', 'cassini_iss.vic', {}, 'png'),
    ('output_tiff', 'cassini_iss.vic', {}, 'tiff'),
    ('output_tiff16', 'cassini_iss.vic', {'twobytes': True}, 'tiff'),
]

ENHANCEMENT_GALLERY: list[tuple[str, str, dict[str, Any], str]] = [
    ('enhance_default', 'galileo_ssi_a.vic', {}, 'jpg'),
    ('enhance_pct5_95', 'galileo_ssi_a.vic', {'percentiles': (5.0, 95.0)}, 'jpg'),
    ('enhance_gamma2', 'galileo_ssi_a.vic', {'gamma': 2.0}, 'jpg'),
    ('enhance_colormap', 'galileo_ssi_a.vic', {'colormap': 'red-blue'}, 'jpg'),
    ('enhance_histogram', 'galileo_ssi_a.vic', {'histogram': True}, 'jpg'),
    ('enhance_tint', 'galileo_ssi_a.vic', {'tint': True}, 'jpg'),
]

GEOMETRY_GALLERY: list[tuple[str, str, dict[str, Any], str]] = [
    ('geom_default', 'cassini_iss.vic', {}, 'jpg'),
    ('geom_scale200', 'cassini_iss.vic', {'scale': (200.0, 200.0)}, 'jpg'),
    ('geom_frame_pad', 'cassini_iss.vic', {'frame': (64, 64), 'pad': True}, 'jpg'),
    ('geom_frame_max_50', 'cassini_iss.vic', {'frame_max': 50}, 'jpg'),
    ('geom_rot90', 'cassini_iss.vic', {'rotate': 'rot90'}, 'jpg'),
]

ALL_GALLERIES = (
    INSTRUMENT_GALLERY
    + OUTPUT_FORMAT_GALLERY
    + ENHANCEMENT_GALLERY
    + GEOMETRY_GALLERY
)


def _generate_one(
    slug: str,
    fixture_name: str,
    kwargs: dict[str, Any],
    ext: str,
    out_dir: Path,
) -> Path | None:
    """Render one thumbnail to ``out_dir/<slug>.<ext>``.

    Parameters:
        slug: Output stem (e.g. ``cassini_iss_tint``).
        fixture_name: File name under ``tests/fixtures/``.
        kwargs: Keyword arguments forwarded to ``images_to_pics``.
        ext: Output extension (``jpg``, ``png``, ``tiff``).
        out_dir: Final destination directory.

    Returns:
        The produced path, or ``None`` on failure.
    """
    fixture = FIXTURES / fixture_name
    if not fixture.exists():
        print(f'  SKIP {slug}: fixture {fixture_name} missing')
        return None

    # Render to a scratch directory using images_to_pics's default
    # naming, then move into place. This avoids the corner case where
    # `strip=[<stem>]` leaves a leading dot in the basename, which
    # turns the output into a hidden file.
    with tempfile.TemporaryDirectory() as scratch:
        scratch_path = Path(scratch)
        try:
            images_to_pics(
                [str(fixture)],
                directory=str(scratch_path),
                extension=ext,
                replace='all',
                **kwargs,
            )
        except Exception as exc:
            print(f'  FAIL {slug}: {type(exc).__name__}: {exc}')
            return None

        produced = scratch_path / f'{Path(fixture_name).stem}.{ext}'
        if not produced.exists():
            print(f'  MISSING {slug}: expected {produced.name} in scratch')
            return None

        final = out_dir / f'{slug}.{ext}'
        shutil.copyfile(produced, final)
        return final


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    survivors = 0
    for slug, fixture_name, kwargs, ext in ALL_GALLERIES:
        path = _generate_one(slug, fixture_name, kwargs, ext, OUT_DIR)
        if path is not None:
            survivors += 1
            print(f'  ok {path.name}')
    print(f'\nemitted {survivors}/{len(ALL_GALLERIES)} thumbnails to {OUT_DIR}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
