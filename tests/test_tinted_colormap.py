"""tinted_colormap: tint + HST wavelength-inference + dict-lookup paths."""

from __future__ import annotations

import pytest

from picmaker.picmaker import tinted_colormap


class TestNoneInputs:
    def test_none_filter_info(self) -> None:
        assert tinted_colormap(None) is None

    def test_none_filter_name(self) -> None:
        assert tinted_colormap(('HST', 'WFC3', None)) is None


class TestCassiniTints:
    def test_cl1_grn_picks_green_tint(self) -> None:
        # 'CL1+GRN' contains "GRN" (not "BL", not "RED") → (110,190,110).
        result = tinted_colormap(('CASSINI', 'ISS', 'CL1+GRN'))
        assert result == [(0, 0, 0), (110, 190, 110), (255, 255, 255)]

    def test_red_filter_picks_red_tint(self) -> None:
        result = tinted_colormap(('CASSINI', 'ISS', 'CL1+RED'))
        assert result == [(0, 0, 0), (190, 110, 100), (255, 255, 255)]

    def test_uv_filter_picks_uv_tint(self) -> None:
        result = tinted_colormap(('CASSINI', 'ISS', 'CL1+UV1'))
        assert result == [(0, 0, 0), (160, 80, 220), (255, 255, 255)]

    def test_bl_grn_picks_combo_tint(self) -> None:
        # 'BL' substring → blue branch; 'GRN' inside → combo tint.
        result = tinted_colormap(('CASSINI', 'ISS', 'BL1+GRN'))
        assert result == [(0, 0, 0), (110, 180, 180), (255, 255, 255)]

    def test_unknown_filter_falls_back_to_gray(self) -> None:
        result = tinted_colormap(('CASSINI', 'ISS', 'XYZ'))
        assert result == [(0, 0, 0), (127, 127, 127), (255, 255, 255)]


class TestVoyagerLookup:
    def test_green_filter(self) -> None:
        result = tinted_colormap(('VOYAGER', 'ISS', 'GREEN'))
        assert result == [(0, 0, 0), (110, 255, 110), (255, 255, 255)]

    def test_blue_filter(self) -> None:
        result = tinted_colormap(('VOYAGER', 'ISS', 'BLUE'))
        assert result == [(0, 0, 0), (110, 110, 255), (255, 255, 255)]


class TestGalileoLookup:
    def test_green_filter(self) -> None:
        result = tinted_colormap(('GALILEO', 'SSI', 'GREEN'))
        assert result == [(0, 0, 0), (110, 190, 110), (255, 255, 255)]

    def test_red_filter(self) -> None:
        result = tinted_colormap(('GALILEO', 'SSI', 'RED'))
        assert result == [(0, 0, 0), (190, 130, 100), (255, 255, 255)]


class TestNhMvicLookup:
    def test_blue_filter(self) -> None:
        result = tinted_colormap(('NEW HORIZONS', 'MVIC', 'BLUE'))
        assert result == [(0, 0, 0), (110, 110, 210), (255, 255, 255)]

    def test_nir_filter(self) -> None:
        result = tinted_colormap(('NEW HORIZONS', 'MVIC', 'NIR'))
        assert result == [(0, 0, 0), (210, 65, 45), (255, 255, 255)]


class TestHstWavelengthInference:
    def test_f606w_returns_grayscale(self) -> None:
        # F606W is in the special list → grayscale (no tint).
        assert tinted_colormap(('HST', 'WFC3/UVIS', 'F606W')) == [
            (0, 0, 0),
            (255, 255, 255),
        ]

    def test_f555w_picks_green_via_wavelength(self) -> None:
        # 555 → green range.
        result = tinted_colormap(('HST', 'WFC3', 'F555W'))
        assert result is not None
        assert len(result) == 3
        # Mid colour: green dominant.
        _, tint, _ = result
        r, g, b = tint
        assert g > r and g > b

    def test_unknown_filter_returns_none(self) -> None:
        # Triggers the print('******UNKNOWN FILTER:', ...) path; pre-PR3 it
        # remains a print(), PR 3 will switch to logger.warning().
        assert tinted_colormap(('HST', 'WFC3', 'UNKNOWN_FILTER_XYZ')) is None
