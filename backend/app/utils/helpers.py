from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def generate_uuid() -> str:
    """Generate a string UUID for identifiers and storage keys."""
    return str(uuid4())


def compact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Drop keys whose values are None so API payloads stay concise."""
    return {key: value for key, value in data.items() if value is not None}


def round_decimal(value: float | Decimal, places: int = 2) -> Decimal:
    """Round numeric values using financial half-up semantics."""
    quantizer = Decimal("1").scaleb(-places)
    return Decimal(str(value)).quantize(quantizer, rounding=ROUND_HALF_UP)
