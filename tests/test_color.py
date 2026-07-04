"""ColorNames.lookup tests."""

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
    """Test error handling for invalid color name lookups."""

    def test_unknown_name_raises(self) -> None:
        with pytest.raises(KeyError) as excinfo:
            ColorNames.lookup('not_a_real_color')
        assert 'not_a_real_color' in str(excinfo.value)

    def test_empty_string_raises(self) -> None:
        with pytest.raises(KeyError) as excinfo:
            ColorNames.lookup('')
        assert 'unrecognized color name' in str(excinfo.value)

    def test_hex_code_not_supported(self) -> None:
        # ColorNames.lookup recognizes only X11 names and (r,g,b)/[r,g,b]
        # expressions. Hex codes are NOT supported today; PR 3 may add them.
        with pytest.raises(KeyError) as excinfo:
            ColorNames.lookup('#ff8800')
        assert '#ff8800' in str(excinfo.value)

    def test_non_string_raises_typeerror(self) -> None:
        # Deliberately passing an int to exercise the TypeError branch.
        with pytest.raises(TypeError) as excinfo:
            ColorNames.lookup(42)
        assert 'Colorname must be a string' in str(excinfo.value)


class TestRgbExpression:
    """Test RGB tuple and bracket expression parsing."""

    def test_rgb_tuple_expression(self) -> None:
        assert ColorNames.lookup('(255, 128, 0)') == (255, 128, 0)

    def test_rgb_brackets_expression(self) -> None:
        # Bracket form `[100, 100, 100]` parses via ast.literal_eval and is
        # normalized to a ``(r, g, b)`` tuple before being returned, so the
        # two bracketing styles produce identical results.
        assert ColorNames.lookup('[100, 100, 100]') == (100, 100, 100)

    def test_rgb_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match='RGB value cannot exceed 255'):
            ColorNames.lookup('(300, 0, 0)')

    def test_rgb_partial_match_raises_keyerror(self) -> None:
        """A regex match that doesn't span the whole input is rejected.

        Regression: previously the function silently returned None when the
        RGB regex matched a prefix; callers expected a KeyError.
        """
        with pytest.raises(KeyError, match='unrecognized color name'):
            ColorNames.lookup('(1, 2, 3) garbage')

    def test_rgb_injection_payload_rejected(self) -> None:
        """A trailing expression after the RGB tuple is rejected.

        Regression: the parser must not allow arbitrary Python expressions
        appended to a valid-looking RGB triple. `ast.literal_eval` and the
        end-of-string regex check together guarantee this.
        """
        with pytest.raises(KeyError, match='unrecognized color name'):
            ColorNames.lookup('(1, 2, 3); __import__("os").system("ls")')
