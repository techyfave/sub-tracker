from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

_CENT = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Money:
    """A monetary amount represented without floating-point arithmetic."""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        currency = self.currency.strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a three-letter code")

        if not self.amount.is_finite():
            raise ValueError("amount must be finite")

        normalized_amount = self.amount.quantize(
            _CENT,
            rounding=ROUND_HALF_EVEN,
        )

        object.__setattr__(self, "amount", normalized_amount)
        object.__setattr__(self, "currency", currency)
