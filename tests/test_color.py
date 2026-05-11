"""ColorNames.lookup tests."""

from __future__ import annotations

import pytest

from picmaker.colornames import ColorNames


class TestPositiveLookups:
    def test_lowercase_red(self) -> None:
        assert ColorNames.lookup('red') == (255, 0, 0)

    def test_camelcase_ghostwhite(self) -> None:
        assert ColorNames.lookup('GhostWhite') == (248, 248, 255)

    def test_whitespace_normalized(self) -> None:
        # Lookup squashes spaces/dashes/underscores.
        assert ColorNames.lookup('ghost white') == (248, 248, 255)
        assert ColorNames.lookup('  white  ') == (255, 255, 255)


class TestNegativeLookups:
    def test_unknown_name_raises(self) -> None:
        with pytest.raises(KeyError):
            ColorNames.lookup('not_a_real_color')

    def test_empty_string_raises(self) -> None:
        with pytest.raises(KeyError):
            ColorNames.lookup('')

    def test_hex_code_not_supported(self) -> None:
        # ColorNames.lookup recognizes only X11 names and (r,g,b)/[r,g,b]
        # expressions. Hex codes are NOT supported today; PR 3 may add them.
        with pytest.raises(KeyError):
            ColorNames.lookup('#ff8800')

    def test_non_string_raises_typeerror(self) -> None:
        with pytest.raises(TypeError):
            ColorNames.lookup(42)


class TestRgbExpression:
    def test_rgb_tuple_expression(self) -> None:
        assert ColorNames.lookup('(255, 128, 0)') == (255, 128, 0)

    def test_rgb_brackets_expression(self) -> None:
        # Bracket form `[100, 100, 100]` parses but returns a list (eval result),
        # not a tuple — documenting the actual current behavior.
        assert ColorNames.lookup('[100, 100, 100]') == [100, 100, 100]

    def test_rgb_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match='Color value out of range'):
            ColorNames.lookup('(300, 0, 0)')
