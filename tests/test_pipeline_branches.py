"""Cover the pipeline branches that the snapshot / smoke tests miss:
mutex checks, movie mode, the ``--proceed`` error path, ``--zebra``,
HST mosaic dispatch, and the reuse path of ``process_images``.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from picmaker.pipeline import images_to_pics, process_images

# ---------------------------------------------------------------------------
# Mutex / value-validity checks inside images_to_pics
# ---------------------------------------------------------------------------


def test_hst_bands_incompatible(fixtures_dir: Path, tmp_path: Path) -> None:
    """``hst=True`` plus ``bands=...`` is rejected before any I/O."""
    with pytest.raises(ValueError, match='hst and bands'):
        images_to_pics(
            [str(fixtures_dir / 'cassini_iss.vic')],
            directory=str(tmp_path),
            hst=True,
            bands=(0, 1),
        )


def test_frame_size_incompatible(fixtures_dir: Path, tmp_path: Path) -> None:
    """``frame`` plus ``size`` is rejected before any I/O."""
    with pytest.raises(ValueError, match='frame and size'):
        images_to_pics(
            [str(fixtures_dir / 'cassini_iss.vic')],
            directory=str(tmp_path),
            frame=(50, 50),
            size=(20, 20),
        )


def test_frame_wrap_ratio_incompatible(fixtures_dir: Path, tmp_path: Path) -> None:
    """``frame`` plus ``wrap_ratio`` is rejected before any I/O."""
    with pytest.raises(ValueError, match='frame and wrap_ratio'):
        images_to_pics(
            [str(fixtures_dir / 'cassini_iss.vic')],
            directory=str(tmp_path),
            frame=(50, 50),
            wrap_ratio=2.0,
        )


# ---------------------------------------------------------------------------
# extension default selection
# ---------------------------------------------------------------------------


def test_extension_default_jpg(fixtures_dir: Path, tmp_path: Path) -> None:
    """``extension=None`` defaults to ``'jpg'`` when not twobytes."""
    images_to_pics(
        [str(fixtures_dir / 'cassini_iss.vic')],
        directory=str(tmp_path),
        extension=None,
        replace='all',
    )
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_extension_default_tiff_when_twobytes(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``extension=None`` plus ``twobytes=True`` defaults to ``'tiff'``."""
    images_to_pics(
        [str(fixtures_dir / 'cassini_iss.vic')],
        directory=str(tmp_path),
        extension=None,
        twobytes=True,
        replace='all',
    )
    assert (tmp_path / 'cassini_iss.tiff').exists()


# ---------------------------------------------------------------------------
# replace='none' skip when file exists
# ---------------------------------------------------------------------------


def test_replace_none_skips_existing(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """When the output already exists and ``replace='none'``, the file
    is left in place (``get_outfile`` returns ''; the loop continues)."""
    out = tmp_path / 'cassini_iss.jpg'
    out.write_bytes(b'sentinel')
    images_to_pics(
        [str(fixtures_dir / 'cassini_iss.vic')],
        directory=str(tmp_path),
        replace='none',
    )
    assert out.read_bytes() == b'sentinel'


# ---------------------------------------------------------------------------
# zebra fill and verbose
# ---------------------------------------------------------------------------


def test_zebra_path(fixtures_dir: Path, tmp_path: Path) -> None:
    """``zebra=True`` runs ``fill_zebra_stripes`` without crashing."""
    images_to_pics(
        [str(fixtures_dir / 'cassini_iss.vic')],
        directory=str(tmp_path),
        zebra=True,
        replace='all',
    )
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_verbose_emits_log(
    fixtures_dir: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """``verbose=True`` logs the input filename via ``picmaker.pipeline``."""
    import logging
    with caplog.at_level(logging.INFO, logger='picmaker.pipeline'):
        images_to_pics(
            [str(fixtures_dir / 'cassini_iss.vic')],
            directory=str(tmp_path),
            verbose=True,
            replace='all',
        )
    assert 'cassini_iss.vic' in caplog.text


# ---------------------------------------------------------------------------
# --proceed error path
# ---------------------------------------------------------------------------


def test_proceed_swallows_errors(
    fixtures_dir: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """``proceed=True`` logs and continues past a per-file failure."""
    import logging
    bogus = tmp_path / 'bogus.bin'
    bogus.write_bytes(b'not-an-image')
    good = fixtures_dir / 'cassini_iss.vic'

    with caplog.at_level(logging.ERROR, logger='picmaker.pipeline'):
        images_to_pics(
            [str(bogus), str(good)],
            directory=str(tmp_path),
            proceed=True,
            replace='all',
        )

    assert 'bogus.bin' in caplog.text
    # The well-formed fixture still produces its output.
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_no_proceed_raises_on_first_error(
    tmp_path: Path,
) -> None:
    """``proceed=False`` (the default) re-raises on the first failure."""
    bogus = tmp_path / 'bogus.bin'
    bogus.write_bytes(b'not-an-image')
    with pytest.raises(OSError, match='Unrecognized image file format'):
        images_to_pics([str(bogus)], directory=str(tmp_path))


# ---------------------------------------------------------------------------
# HST mosaic
# ---------------------------------------------------------------------------


def test_hst_acs_mosaic_writes_output(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``hst=True`` on an ACS/WFC fixture writes a single mosaicked JPG."""
    images_to_pics(
        [str(fixtures_dir / 'hst_acs.fits')],
        directory=str(tmp_path),
        hst=True,
        replace='all',
    )
    assert (tmp_path / 'hst_acs.jpg').exists()


def test_hst_wfpc2_mosaic_writes_output(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``hst=True`` on a WFPC2 fixture writes a single mosaicked JPG."""
    images_to_pics(
        [str(fixtures_dir / 'hst_wfpc2.fits')],
        directory=str(tmp_path),
        hst=True,
        replace='all',
    )
    assert (tmp_path / 'hst_wfpc2.jpg').exists()


def test_hst_mosaic_with_zebra(fixtures_dir: Path, tmp_path: Path) -> None:
    """``hst=True`` plus ``zebra=True`` runs ``fill_zebra_stripes`` inside
    the per-detector loop without crashing.
    """
    images_to_pics(
        [str(fixtures_dir / 'hst_acs.fits')],
        directory=str(tmp_path),
        hst=True,
        zebra=True,
        replace='all',
    )
    assert (tmp_path / 'hst_acs.jpg').exists()


# ---------------------------------------------------------------------------
# process_images
# ---------------------------------------------------------------------------


def _basic_option_dict() -> dict[str, Any]:
    """Return a minimal ``option_dict`` compatible with ``images_to_pics``."""
    return {
        'replace': 'all',
        'proceed': False,
        'extension': 'jpg',
        'suffix': '',
        'strip': [],
        'quality': 75,
        'twobytes': False,
        'bands': (0, 1),
        'lines': None,
        'samples': None,
        'obj': None,
        'pointer': ['IMAGE'],
        'size': None,
        'scale': (100.0, 100.0),
        'crop': None,
        'frame': None,
        'pad': False,
        'pad_color': 'black',
        'frame_max': None,
        'wrap': False,
        'wrap_ratio': None,
        'overlap': (0.0, 0.0),
        'gap_size': 1,
        'gap_color': 'white',
        'hst': False,
        'valid': None,
        'limits': None,
        'percentiles': (0.0, 100.0),
        'trim': 0,
        'trim_zeros': False,
        'footprint': 0,
        'histogram': False,
        'colormap': None,
        'below_color': None,
        'above_color': None,
        'invalid_color': 'black',
        'gamma': 1.0,
        'tint': False,
        'display_upward': False,
        'display_downward': False,
        'rotate': 'none',
        'filter': 'none',
        'zebra': False,
    }


def test_process_images_creates_output_directory(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``process_images`` creates the output directory tree if missing."""
    out_dir = tmp_path / 'fresh' / 'subdir'
    process_images(
        [str(fixtures_dir / 'cassini_iss.vic')],
        str(out_dir),
        False,
        [_basic_option_dict()],
    )
    assert out_dir.is_dir()
    assert (out_dir / 'cassini_iss.jpg').exists()


def test_process_images_movie_mode(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """Movie mode runs ``images_to_pics`` twice sharing one stretch."""
    # Use two copies of the same fixture so movie mode has multiple frames
    # to pick a shared stretch across.
    src1 = tmp_path / 'frame_001.vic'
    src2 = tmp_path / 'frame_002.vic'
    shutil.copy(fixtures_dir / 'cassini_iss.vic', src1)
    shutil.copy(fixtures_dir / 'cassini_iss.vic', src2)

    out_dir = tmp_path / 'out'
    process_images(
        [str(src1), str(src2)],
        str(out_dir),
        True,
        [_basic_option_dict()],
    )
    assert (out_dir / 'frame_001.jpg').exists()
    assert (out_dir / 'frame_002.jpg').exists()


def test_process_images_movie_failure_with_proceed(tmp_path: Path) -> None:
    """Movie mode with ``proceed=True`` returns silently on total failure."""
    bogus = tmp_path / 'b.bin'
    bogus.write_bytes(b'garbage')
    od = _basic_option_dict()
    od['proceed'] = True
    # No exception even though no input is readable.
    process_images([str(bogus)], str(tmp_path / 'out'), True, [od])


def test_process_images_movie_failure_raises(tmp_path: Path) -> None:
    """Movie mode without ``proceed`` raises ``OSError`` when no frame
    can be read.
    """
    bogus = tmp_path / 'b.bin'
    bogus.write_bytes(b'garbage')
    od = _basic_option_dict()
    od['proceed'] = False
    # The first read failure propagates out of the inner images_to_pics
    # call rather than hitting the "unable to process movie" guard,
    # because proceed=False re-raises before the movie pass finishes.
    with pytest.raises((OSError, Exception)):
        process_images([str(bogus)], str(tmp_path / 'out'), True, [od])


def test_process_images_reuse_path(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """When two consecutive ``option_dicts`` share ``obj`` and ``pointer``,
    the second pass reuses the read result without rereading the file.
    """
    od1 = _basic_option_dict()
    od1['suffix'] = '_v1'
    od2 = _basic_option_dict()
    od2['suffix'] = '_v2'
    od2['gamma'] = 2.0

    process_images(
        [str(fixtures_dir / 'cassini_iss.vic')],
        str(tmp_path),
        False,
        [od1, od2],
    )
    assert (tmp_path / 'cassini_iss_v1.jpg').exists()
    assert (tmp_path / 'cassini_iss_v2.jpg').exists()


# ---------------------------------------------------------------------------
# wrap_image branch in images_to_pics
# ---------------------------------------------------------------------------


def test_wrap_branch_when_image_elongated(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``wrap=True`` plus an elongated ``--size`` triggers ``wrap_image``."""
    images_to_pics(
        [str(fixtures_dir / 'cassini_iss.vic')],
        directory=str(tmp_path),
        wrap=True,
        size=(120, 16),
        replace='all',
    )
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_pad_branch_runs(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``frame`` plus ``pad=True`` writes a padded output."""
    images_to_pics(
        [str(fixtures_dir / 'cassini_iss.vic')],
        directory=str(tmp_path),
        frame=(64, 64),
        pad=True,
        replace='all',
    )
    out = tmp_path / 'cassini_iss.jpg'
    assert out.exists()


# ---------------------------------------------------------------------------
# Empty input returns triple of Nones
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# PDS3 detached-label branch in images_to_pics
# ---------------------------------------------------------------------------


_LBL_TEMPLATE = """PDS_VERSION_ID = PDS3
INSTRUMENT_HOST_ID = 'CASSINI'
INSTRUMENT_ID = 'ISS'
DETECTOR_ID = 'NAC'
FILTER_NAME = ('CL1', 'GRN')
^IMAGE = "{image_filename}"
OBJECT = IMAGE
  LINES = 16
  LINE_SAMPLES = 16
  SAMPLE_BITS = 8
  SAMPLE_TYPE = UNSIGNED_INTEGER
END_OBJECT = IMAGE
END
"""


def _make_label_pointing_at(fixtures_dir: Path, tmp_path: Path, image: str) -> Path:
    """Copy ``image`` from the fixtures dir to ``tmp_path`` and write a
    PDS3 .LBL alongside that points at it.
    """
    shutil.copy(fixtures_dir / image, tmp_path / image)
    lbl = tmp_path / 'sample.LBL'
    lbl.write_text(_LBL_TEMPLATE.format(image_filename=image))
    return lbl


def test_pds3_label_redirects_to_vicar(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """A ``.LBL`` whose ``^IMAGE`` points at a VICAR file is parsed for
    its label metadata and the VICAR reader handles the actual pixels.
    """
    lbl = _make_label_pointing_at(fixtures_dir, tmp_path, 'cassini_iss.vic')
    out_dir = tmp_path / 'out'
    images_to_pics([str(lbl)], directory=str(out_dir), replace='all')
    assert (out_dir / 'sample.jpg').exists()


_LBL_TUPLE_POINTER = """PDS_VERSION_ID = PDS3
INSTRUMENT_HOST_ID = 'CASSINI'
INSTRUMENT_ID = 'ISS'
FILTER_NAME = ('CL1', 'GRN')
^IMAGE = ("cassini_iss.vic", 1)
END
"""


def test_pds3_label_tuple_pointer(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """A pointer specified as ``(filename, record)`` is normalised to the
    filename component.
    """
    shutil.copy(fixtures_dir / 'cassini_iss.vic', tmp_path / 'cassini_iss.vic')
    lbl = tmp_path / 'tuple.LBL'
    lbl.write_text(_LBL_TUPLE_POINTER)
    out_dir = tmp_path / 'out'
    images_to_pics([str(lbl)], directory=str(out_dir), replace='all')
    assert (out_dir / 'tuple.jpg').exists()


_LBL_LIST_POINTER = """PDS_VERSION_ID = PDS3
INSTRUMENT_HOST_ID = 'CASSINI'
INSTRUMENT_ID = 'ISS'
^IMAGE = ("frame_a.vic", "frame_b.vic")
END
"""


def test_pds3_label_list_pointer_obj_none_picks_all(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """A pointer specified as a list of filenames stacks every entry when
    ``obj`` is not given.
    """
    shutil.copy(fixtures_dir / 'cassini_iss.vic', tmp_path / 'frame_a.vic')
    shutil.copy(fixtures_dir / 'cassini_iss.vic', tmp_path / 'frame_b.vic')
    lbl = tmp_path / 'multi.LBL'
    lbl.write_text(_LBL_LIST_POINTER)
    out_dir = tmp_path / 'out'
    images_to_pics([str(lbl)], directory=str(out_dir), replace='all')
    assert (out_dir / 'multi.jpg').exists()


def test_pds3_label_list_pointer_obj_int_picks_one(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``obj=0`` selects a single entry from a list-of-files pointer."""
    shutil.copy(fixtures_dir / 'cassini_iss.vic', tmp_path / 'frame_a.vic')
    shutil.copy(fixtures_dir / 'cassini_iss.vic', tmp_path / 'frame_b.vic')
    lbl = tmp_path / 'multi.LBL'
    lbl.write_text(_LBL_LIST_POINTER)
    out_dir = tmp_path / 'out'
    images_to_pics([str(lbl)], directory=str(out_dir), obj=0, replace='all')
    assert (out_dir / 'multi.jpg').exists()


def test_pds3_label_missing_pointer_raises(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """A label that doesn't contain the requested pointer raises ``KeyError``."""
    lbl = tmp_path / 'no_pointer.LBL'
    lbl.write_text("""PDS_VERSION_ID = PDS3
INSTRUMENT_HOST_ID = 'CASSINI'
END
""")
    with pytest.raises(KeyError, match=r'PDS pointer .* not found'):
        images_to_pics([str(lbl)], directory=str(tmp_path), replace='all')


def test_pds3_label_obj_out_of_range_raises(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``obj=999`` against a single-pointer label raises ``IndexError``."""
    lbl = _make_label_pointing_at(fixtures_dir, tmp_path, 'cassini_iss.vic')
    with pytest.raises(IndexError, match='out of range'):
        images_to_pics([str(lbl)], directory=str(tmp_path / 'out'),
                       obj=999, replace='all')


def test_pds3_label_uses_spacecraft_id_fallback(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """Without ``INSTRUMENT_HOST_ID``, ``SPACECRAFT_ID`` is used instead."""
    shutil.copy(fixtures_dir / 'cassini_iss.vic', tmp_path / 'cassini_iss.vic')
    lbl = tmp_path / 'sc.LBL'
    lbl.write_text("""PDS_VERSION_ID = PDS3
SPACECRAFT_ID = 'CASSINI'
INSTRUMENT_ID = 'ISS'
DETECTOR_ID = 'NAC'
FILTER_NAME = ('CL1', 'GRN')
^IMAGE = "cassini_iss.vic"
END
""")
    out_dir = tmp_path / 'out'
    images_to_pics([str(lbl)], directory=str(out_dir), replace='all')
    assert (out_dir / 'sc.jpg').exists()


def test_pds3_label_uses_spacecraft_name_fallback(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``SPACECRAFT_NAME`` is the last fallback for the host."""
    shutil.copy(fixtures_dir / 'cassini_iss.vic', tmp_path / 'cassini_iss.vic')
    lbl = tmp_path / 'scn.LBL'
    lbl.write_text("""PDS_VERSION_ID = PDS3
SPACECRAFT_NAME = 'CASSINI'
INSTRUMENT_NAME = 'ISS'
^IMAGE = "cassini_iss.vic"
END
""")
    out_dir = tmp_path / 'out'
    images_to_pics([str(lbl)], directory=str(out_dir), replace='all')
    assert (out_dir / 'scn.jpg').exists()


def test_empty_input_returns_none_triple(tmp_path: Path) -> None:
    """An empty filename list returns ``(None, None, None)``."""
    result = images_to_pics([], directory=str(tmp_path))
    assert result == (None, None, None)


# ---------------------------------------------------------------------------
# Display upward / downward overrides
# ---------------------------------------------------------------------------


def test_display_upward_override(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``display_upward=True`` overrides the per-instrument default."""
    images_to_pics(
        [str(fixtures_dir / 'cassini_iss.vic')],
        directory=str(tmp_path),
        display_upward=True,
        replace='all',
    )
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_display_downward_override(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``display_downward=True`` overrides the per-instrument default."""
    images_to_pics(
        [str(fixtures_dir / 'cassini_iss.vic')],
        directory=str(tmp_path),
        display_downward=True,
        replace='all',
    )
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_tint_with_no_filter_info_skips_override(
    tmp_path: Path,
) -> None:
    """``tint=True`` on an image with no ``filter_info`` leaves the
    requested colormap in place (the override path is a no-op).
    """
    # A plain numpy array has no filter_info; tinted_colormap returns None.
    src = tmp_path / 'plain.npy'
    np.save(src, (np.arange(64).reshape(8, 8) * 4).astype('uint8'))
    images_to_pics(
        [str(src)],
        directory=str(tmp_path),
        tint=True,
        replace='all',
    )
    assert (tmp_path / 'plain.jpg').exists()
