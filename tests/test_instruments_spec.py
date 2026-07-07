"""Spec tests for the instrument readers, derived from their docstrings.

Every ``detect_in_*`` method documents that it returns its instrument subclass
when the label/header describes that instrument, and ``None`` otherwise. These
tests drive the documented ``None`` branch with minimal fakes (no fixture files
needed, since detection rejects a non-matching product before reading pixels).

The Cassini tint categories asserted here are the ones documented in the User
Guide, section 6 (Supported instruments and formats): a recognized color/
narrowband filter yields an (R, G, B) tint, while a clear or unknown filter
yields no tint (``None``), which the pipeline renders as neutral gray.
"""

import pytest

from picmaker.instruments.cassini_iss import Cassini_ISS
from picmaker.instruments.galileo_ssi import Galileo_SSI
from picmaker.instruments.hst_acs import HST_ACS
from picmaker.instruments.hst_nicmos import HST_NICMOS
from picmaker.instruments.hst_wfpc2 import HST_WFPC2
from picmaker.instruments.nh_lorri import NH_LORRI
from picmaker.instruments.nh_mvic import NH_MVIC
from picmaker.instruments.voyager_iss import Voyager_ISS


class _HDU:
    """Minimal stand-in for a single FITS HDU exposing a ``.header`` mapping."""

    def __init__(self, header: dict[str, str]) -> None:
        self.header = header


# --- detection returns None for a non-matching product ---------------------


def test_cassini_rejects_foreign_pds3() -> None:
    assert Cassini_ISS.detect_in_pds3({'INSTRUMENT_HOST_NAME': 'OTHER'}, 'x') is None


def test_cassini_rejects_wrong_instrument_pds3() -> None:
    """A Cassini host with a non-ISS instrument is not a Cassini ISS product."""
    assert Cassini_ISS.detect_in_pds3(
        {'INSTRUMENT_HOST_NAME': 'CASSINI ORBITER', 'INSTRUMENT_ID': 'XXX'}, 'x') is None


def test_cassini_rejects_foreign_vicar() -> None:
    assert Cassini_ISS.detect_in_vicar({'INSTRUMENT_HOST_NAME': 'OTHER'}, 'x') is None
    assert Cassini_ISS.detect_in_vicar(
        {'INSTRUMENT_HOST_NAME': 'CASSINI ORBITER', 'INSTRUMENT_ID': 'XX'}, 'x') is None


def test_voyager_rejects_foreign_pds3() -> None:
    assert Voyager_ISS.detect_in_pds3({'INSTRUMENT_HOST_NAME': 'OTHER'}, 'x') is None
    assert Voyager_ISS.detect_in_pds3(
        {'INSTRUMENT_HOST_NAME': 'VOYAGER 1', 'INSTRUMENT_ID': 'XXX'}, 'x') is None


def test_voyager_rejects_foreign_vicar() -> None:
    assert Voyager_ISS.detect_in_vicar(
        {'LAB02': 'ABC', 'LAB03': 'x' * 10}, 'x') is None


def test_galileo_rejects_foreign_pds3() -> None:
    assert Galileo_SSI.detect_in_pds3({'SPACECRAFT_NAME': 'OTHER'}, 'x') is None
    assert Galileo_SSI.detect_in_pds3(
        {'SPACECRAFT_NAME': 'GALILEO ORBITER', 'INSTRUMENT_NAME': 'OTHER'}, 'x') is None


def test_galileo_rejects_foreign_vicar() -> None:
    assert Galileo_SSI.detect_in_vicar({'MISSION': 'OTHER'}, 'x') is None
    assert Galileo_SSI.detect_in_vicar(
        {'MISSION': 'GALILEO', 'SENSOR': 'XX'}, 'x') is None


def test_nh_mvic_rejects_foreign_pds3() -> None:
    assert NH_MVIC.detect_in_pds3({'INSTRUMENT_HOST_ID': 'OTHER'}, 'x') is None
    assert NH_MVIC.detect_in_pds3(
        {'INSTRUMENT_HOST_ID': 'NH', 'INSTRUMENT_ID': 'OTHER'}, 'x') is None


def test_nh_mvic_rejects_foreign_fits() -> None:
    assert NH_MVIC.detect_in_fits([_HDU({'HOSTNAME': 'OTHER'})], 'x') is None


def test_nh_lorri_rejects_foreign_pds3() -> None:
    assert NH_LORRI.detect_in_pds3({'INSTRUMENT_HOST_ID': 'OTHER'}, 'x') is None


def test_nh_lorri_rejects_foreign_fits() -> None:
    assert NH_LORRI.detect_in_fits([_HDU({'HOSTNAME': 'OTHER'})], 'x') is None


def test_hst_acs_rejects_foreign_fits() -> None:
    assert HST_ACS.detect_in_fits([_HDU({'TELESCOP': 'NOT-HST'})], 'x') is None
    assert HST_ACS.detect_in_fits(
        [_HDU({'TELESCOP': 'HST', 'INSTRUME': 'OTHER'})], 'x') is None


def test_hst_wfpc2_rejects_foreign_fits() -> None:
    assert HST_WFPC2.detect_in_fits([_HDU({'TELESCOP': 'NOT-HST'})], 'x') is None
    assert HST_WFPC2.detect_in_fits(
        [_HDU({'TELESCOP': 'HST', 'INSTRUME': 'OTHER'})], 'x') is None


def test_hst_nicmos_rejects_foreign_fits() -> None:
    assert HST_NICMOS.detect_in_fits([_HDU({'TELESCOP': 'NOT-HST'})], 'x') is None
    assert HST_NICMOS.detect_in_fits(
        [_HDU({'TELESCOP': 'HST', 'INSTRUME': 'OTHER'})], 'x') is None


# --- Cassini default tint by filter category (User Guide section 6) ---------


@pytest.mark.parametrize(('filter1', 'filter2'), [
    ('IR', ''),          # reddish IR shading
    ('UV', ''),          # violet
    ('VIO', ''),         # violet
    ('BL', ''),          # blue
    ('BL', 'GRN'),       # blue/green
    ('GRN', ''),         # green
    ('GRN', 'RED'),      # green/red
    ('RED', ''),         # red
    ('MT1', ''),         # narrowband methane / H-alpha
    ('CB1', ''),
    ('HAL', ''),
    ('MT', ''),
    ('CB', ''),
])
def test_cassini_known_filters_yield_rgb_tint(filter1: str, filter2: str) -> None:
    """A recognized Cassini filter maps to an (R, G, B) tint triple."""
    tint = Cassini_ISS._default_tint(filter1, filter2)
    assert isinstance(tint, tuple)
    assert len(tint) == 3
    assert all(0 <= c <= 255 for c in tint)


@pytest.mark.parametrize(('filter1', 'filter2'), [
    ('CL1', 'CL2'),      # clear + clear -> no tint (neutral gray)
    ('CL1', 'GREENISH'),  # not a recognized substring
    ('', ''),
])
def test_cassini_clear_or_unknown_yields_no_tint(filter1: str, filter2: str) -> None:
    """Clear or unrecognized filters produce no tint (rendered as gray)."""
    assert Cassini_ISS._default_tint(filter1, filter2) is None
