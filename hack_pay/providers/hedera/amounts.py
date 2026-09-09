"""
hack_pay.providers.hedera.amounts — HBAR amount parsing and validation.

Uses Decimal arithmetic throughout — never float — to avoid rounding errors
in financial calculations.

1 HBAR = 100_000_000 tinybars (8 decimal places).
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

TINYBAR_PER_HBAR: int = 100_000_000

# Accepts: "0.5 HBAR", "1 HBAR", "0.00000001 HBAR" (1 tinybar), "100 hbar"
_HBAR_PATTERN = re.compile(r"^(\d+(?:\.\d{1,8})?)\s+HBAR$", re.IGNORECASE)


def parse_hbar_string(value: str) -> int:
    """
    Parse an HBAR amount string to an integer tinybar value.

    Parameters
    ----------
    value:
        String in the form ``"N HBAR"`` where N has at most 8 decimal places.
        Examples: ``"0.5 HBAR"``, ``"1 HBAR"``, ``"0.00000001 HBAR"``.

    Returns
    -------
    int
        Exact tinybar amount.

    Raises
    ------
    ValueError
        If the format is invalid, amount is zero or negative, or has more
        than 8 decimal places.
    """
    m = _HBAR_PATTERN.match(value.strip())
    if not m:
        raise ValueError(
            f"Invalid HBAR amount: {value!r}. "
            "Expected format: '0.5 HBAR' (up to 8 decimal places)."
        )
    try:
        d = Decimal(m.group(1))
    except InvalidOperation as exc:
        raise ValueError(f"Cannot parse HBAR value {value!r}: {exc}") from exc

    tinybars = int(d * TINYBAR_PER_HBAR)

    # Guard: Decimal round-trip must be exact (catches >8 decimal place edge cases)
    if Decimal(tinybars) != d * TINYBAR_PER_HBAR:
        raise ValueError(
            f"Amount {value!r} has more than 8 decimal places. "
            "Maximum precision is 1 tinybar (0.00000001 HBAR)."
        )
    if tinybars <= 0:
        raise ValueError(f"Payment amount must be positive, got {tinybars} tinybars.")

    return tinybars


def format_tinybars(tinybars: int) -> str:
    """
    Format a tinybar integer as a human-readable HBAR string.

    Used in log messages and error text. Not used for wire protocol values
    (those always use the raw integer string).

    Examples
    --------
    >>> format_tinybars(50_000_000)
    '0.5 HBAR'
    >>> format_tinybars(100_000_000)
    '1 HBAR'
    """
    d = Decimal(tinybars) / TINYBAR_PER_HBAR
    # Remove trailing zeros but keep at least one decimal place if non-integer
    normalised = d.normalize()
    return f"{normalised} HBAR"