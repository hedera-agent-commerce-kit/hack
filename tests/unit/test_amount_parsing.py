"""tests/unit/test_amount_parsing.py — parse_hbar_string and format_tinybars."""

import pytest
from hack_pay.providers.hedera.amounts import (
    TINYBAR_PER_HBAR,
    format_tinybars,
    parse_hbar_string,
)


class TestParseHbarString:
    def test_whole_hbar(self):
        assert parse_hbar_string("1 HBAR") == 100_000_000

    def test_fractional_hbar(self):
        assert parse_hbar_string("0.5 HBAR") == 50_000_000

    def test_one_tinybar(self):
        assert parse_hbar_string("0.00000001 HBAR") == 1

    def test_case_insensitive(self):
        assert parse_hbar_string("1 hbar") == 100_000_000
        assert parse_hbar_string("0.5 Hbar") == 50_000_000

    def test_large_amount(self):
        assert parse_hbar_string("100 HBAR") == 10_000_000_000

    def test_leading_whitespace_stripped(self):
        assert parse_hbar_string("  0.5 HBAR  ") == 50_000_000

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="positive"):
            parse_hbar_string("0 HBAR")

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            parse_hbar_string("-1 HBAR")

    def test_missing_unit_raises(self):
        with pytest.raises(ValueError):
            parse_hbar_string("0.5")

    def test_wrong_unit_raises(self):
        with pytest.raises(ValueError):
            parse_hbar_string("0.5 ETH")

    def test_too_many_decimals_raises(self):
        with pytest.raises(ValueError, match="decimal"):
            parse_hbar_string("0.000000001 HBAR")  # 9 decimal places

    def test_uses_decimal_not_float(self):
        # 0.1 HBAR is exactly 10_000_000 tinybars — no floating point error
        result = parse_hbar_string("0.1 HBAR")
        assert result == 10_000_000

    def test_eight_decimal_places(self):
        assert parse_hbar_string("0.12345678 HBAR") == 12_345_678


class TestFormatTinybars:
    def test_one_hbar(self):
        assert format_tinybars(100_000_000) == "1 HBAR"

    def test_half_hbar(self):
        assert format_tinybars(50_000_000) == "0.5 HBAR"

    def test_one_tinybar(self):
        assert format_tinybars(1) == "1E-8 HBAR"