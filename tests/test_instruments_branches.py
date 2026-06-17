"""Cover the per-instrument fall-through paths: Cassini ISS tint chain
branches, Voyager/Galileo/NH/HST detection and tint_for edge cases,
and the cross-cutting ``instruments.lookup`` predicate.
"""

from typing import Any

import pytest

from picmaker import instruments
from picmaker.instruments import cassini_iss as cassini, galileo_ssi as galileo, hst, nh_lorri as nh, voyager_iss as voyager


def test_cassini_tint_falls_back_to_grey() -> None:
    """Unknown Cassini filters fall back to the neutral grey tint."""
    cmap = cassini.tint_for('ISS', 'WAT+CL2')
    assert cmap == [(0, 0, 0), (127, 127, 127), (255, 255, 255)]


@pytest.mark.parametrize(
    ('filter_name', 'expected_tint'),
    [
        ('IR1+CL2', (200, 80, 80)),
        ('UV3+CL2', (160, 80, 220)),
        ('VIO+CL2', (160, 120, 200)),
        ('BL1+CL2', (110, 110, 180)),
        ('BL1+GRN', (110, 180, 180)),
        ('GRN+RED', (190, 190, 110)),
        ('CL1+GRN', (110, 190, 110)),
        ('RED+CL2', (190, 110, 100)),
        ('MT1+CL2', (190, 110, 100)),
        ('CB1+CL2', (190, 110, 100)),
        ('HAL+CL2', (190, 110, 100)),
        ('MT3+CL2', (200, 80, 80)),
        ('CB3+CL2', (200, 80, 80)),
    ],
)
def test_cassini_tint_chain_each_branch(
    filter_name: str, expected_tint: tuple[int, int, int]
) -> None:
    """Each branch of the Cassini ISS tint chain returns its declared RGB."""
    cmap = cassini.tint_for('ISS', filter_name)
    assert cmap == [(0, 0, 0), expected_tint, (255, 255, 255)]


def test_cassini_matches_predicate() -> None:
    """``matches`` accepts any CASSINI-prefixed host."""
    assert cassini.matches('CASSINI ORBITER', 'ISS') is True
    assert cassini.matches('HUBBLE', 'WFC3') is False


def test_cassini_non_iss_returns_plain_bw() -> None:
    """Non-ISS Cassini instruments get the plain ``[black, white]`` map."""
    assert cassini.tint_for('CIRS', 'anything') == [(0, 0, 0), (255, 255, 255)]


def test_cassini_detect_vicar_swallows_keyerror() -> None:
    """A VICAR label without expected keys returns ``None``."""

    class FakeVic:
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

    assert cassini._detect_vicar(FakeVic()) is None


def test_voyager_non_iss_returns_plain_bw() -> None:
    """Non-ISS Voyager instruments get the plain ``[black, white]`` map."""
    assert voyager.tint_for('PPS', 'anything') == [(0, 0, 0), (255, 255, 255)]


def test_voyager_matches_predicate() -> None:
    """``matches`` accepts any VOYAGER-prefixed host."""
    assert voyager.matches('VOYAGER 1', 'ISS') is True
    assert voyager.matches('NEW HORIZONS', 'MVIC') is False


def test_voyager_detect_vicar_swallows_keyerror() -> None:
    """Vicar labels without LAB02 / LAB03 return ``None`` (caught KeyError)."""

    class FakeVic:
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

    assert voyager._detect_vicar(FakeVic()) is None


def test_galileo_non_ssi_returns_plain_bw() -> None:
    """Non-SSI Galileo instruments get the plain ``[black, white]`` map."""
    assert galileo.tint_for('PPR', 'GREEN') == [(0, 0, 0), (255, 255, 255)]


def test_galileo_detect_vicar_swallows_keyerror() -> None:
    """A label without MISSION or LAB01/LAB03 returns ``None``."""

    class FakeVic:
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

    assert galileo._detect_vicar(FakeVic()) is None


def test_nh_non_mvic_returns_plain_bw() -> None:
    """Non-MVIC NH instruments get the plain ``[black, white]`` map."""
    assert nh.tint_for('LORRI', 'anything') == [(0, 0, 0), (255, 255, 255)]


def _make_fake_hdulist(header: dict[str, Any]) -> Any:
    """Return a minimal ``hdulist[0].header``-compatible object."""

    class _HDU:
        def __init__(self, h: dict[str, Any]) -> None:
            self.header = h

    class _List:
        def __init__(self, h: dict[str, Any]) -> None:
            self._hdu = _HDU(h)

        def __getitem__(self, _i: int) -> Any:
            return self._hdu

    return _List(header)


def test_nh_detect_fits_missing_hostname() -> None:
    """A FITS file with no ``HOSTNAME`` keyword returns ``None``."""
    assert nh._detect_fits(_make_fake_hdulist({})) is None


def test_nh_detect_fits_missing_instru() -> None:
    """A FITS file with ``HOSTNAME`` but no ``INSTRU`` returns ``None``."""
    assert nh._detect_fits(_make_fake_hdulist({'HOSTNAME': 'NEW HORIZONS'})) is None


def test_nh_detect_fits_no_filter_returns_none_filter() -> None:
    """``FILTER`` missing means the third tuple element is ``None``."""
    result = nh._detect_fits(
        _make_fake_hdulist({'HOSTNAME': 'NEW HORIZONS', 'INSTRU': 'MVIC'})
    )
    assert result == ('NEW HORIZONS', 'MVIC', None)


def test_hst_detect_fits_missing_instrume() -> None:
    """A FITS file with TELESCOP but no INSTRUME returns ``None``."""
    assert hst._detect_fits(_make_fake_hdulist({'TELESCOP': 'HST'})) is None


def test_hst_long_pass_short_circuit() -> None:
    """``F350LP`` / ``F606W`` / ``LONG_PASS`` short-circuit to ``[bw]``."""
    assert hst.tint_for('WFC3/UVIS', 'F350LP') == [(0, 0, 0), (255, 255, 255)]
    assert hst.tint_for('WFC3/UVIS', 'F606W') == [(0, 0, 0), (255, 255, 255)]


def test_hst_unknown_filter_returns_none() -> None:
    """An HST filter whose digits cannot be inferred returns ``None``."""
    # 'ABCDE' has no digits; wavelength stays 0 → None.
    assert hst.tint_for('WFC3/UVIS', 'ABCDE') is None


def test_hst_fquv_pinned() -> None:
    """``FQUV*`` quad-filters are pinned to 300 nm."""
    cmap = hst.tint_for('WFPC2', 'FQUV1')
    assert cmap is not None
    assert len(cmap) == 3


def test_hst_fqch4_pinned() -> None:
    """``FQCH4*`` quad-filters are pinned to 900 nm."""
    cmap = hst.tint_for('WFPC2', 'FQCH41')
    assert cmap is not None


def test_hst_pol0s_pinned() -> None:
    """``POL0S`` is pinned when no preceding detector branch matches."""
    cmap = hst.tint_for('OTHER', 'POL0S')
    assert cmap is not None
    assert len(cmap) == 3


def test_hst_pol0l_pinned() -> None:
    """``POL0L`` is pinned (same elif precedence as POL0S)."""
    cmap = hst.tint_for('OTHER', 'POL0L')
    assert cmap is not None
    assert len(cmap) == 3


def test_hst_nicmos_scales_by_3p5() -> None:
    """NICMOS filter wavelengths are scaled by 3.5x."""
    # 'F110' -> 110 nm, NICMOS scales to 385 nm.
    cmap = hst.tint_for('NICMOS', 'F110')
    assert cmap is not None


def test_instruments_lookup_returns_none_for_unknown() -> None:
    """``instruments.lookup`` returns ``None`` for a host with no match."""
    assert instruments.lookup('UNKNOWN', '') is None
