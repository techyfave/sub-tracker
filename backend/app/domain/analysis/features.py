"""Deterministic analysis features.

Pure functions: no database, no clock, no randomness. Same input, same output.
All results are ESTIMATES, not verified savings (see doc/TERMINOLOGY.md).
Rounding rules are documented in backend/docs/analysis-calculations.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.common.money import Money
from app.domain.subscriptions.entities import BillingCadence, Plan


class AnalysisStatus(StrEnum):
    OK = "ok"
    UNSUPPORTED_CADENCE = "unsupported_cadence"
    CURRENCY_MISMATCH = "currency_mismatch"


class UsageLevel(StrEnum):
    UNKNOWN = "unknown"
    UNUSED = "unused"
    USED = "used"


class Freshness(StrEnum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    UNKNOWN = "unknown"


# PLACEHOLDER thresholds: confirm with your teammate before finalizing.
FRESH_MAX_DAYS = 30
AGING_MAX_DAYS = 90

# How many charges happen in one year for each cadence.
_PERIODS_PER_YEAR: dict[BillingCadence, int] = {
    BillingCadence.DAILY: 365,
    BillingCadence.WEEKLY: 52,
    BillingCadence.MONTHLY: 12,
    BillingCadence.YEARLY: 1,
}


@dataclass(frozen=True, slots=True)
class NormalizedCost:
    status: AnalysisStatus
    monthly: Money | None = None
    annual: Money | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class Savings:
    """Estimated savings. Negative values mean the alternative costs MORE."""

    status: AnalysisStatus
    monthly: Money | None = None
    annual: Money | None = None
    detail: str | None = None


def _clean_currency(code: str) -> str:
    return code.strip().upper()


def _exact_costs(amount: Decimal, cadence: BillingCadence | str) -> tuple[Decimal, Decimal] | None:
    """Return (monthly, annual) with NO rounding, or None if cadence unsupported."""
    try:
        parsed = BillingCadence(cadence)
    except ValueError:
        return None
    periods = _PERIODS_PER_YEAR.get(parsed)
    if periods is None:
        return None
    annual = amount * periods
    monthly = annual / 12
    return monthly, annual


def charges_per_year(cadence: BillingCadence | str) -> int | None:
    """How many times per year a cadence charges. None if unsupported."""
    try:
        return _PERIODS_PER_YEAR.get(BillingCadence(cadence))
    except ValueError:
        return None


def normalize_cost(
    amount: Decimal,
    currency: str,
    cadence: BillingCadence | str,
) -> NormalizedCost:
    """Convert a price to monthly and annual cost, rounding once at the end."""
    costs = _exact_costs(amount, cadence)
    if costs is None:
        return NormalizedCost(
            AnalysisStatus.UNSUPPORTED_CADENCE,
            detail=f"unsupported cadence: {cadence!r}",
        )
    monthly, annual = costs
    return NormalizedCost(
        AnalysisStatus.OK,
        monthly=Money(monthly, currency),
        annual=Money(annual, currency),
    )


def classify_usage(event_count: int | None) -> UsageLevel:
    """None means 'we have no data'. It must NEVER be treated as zero."""
    if event_count is None:
        return UsageLevel.UNKNOWN
    if event_count < 0:
        raise ValueError("event_count must not be negative")
    return UsageLevel.UNUSED if event_count == 0 else UsageLevel.USED


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def evidence_freshness(latest_event_at: datetime | None, now: datetime) -> Freshness:
    """How recent the newest evidence is. `now` is passed in to stay pure."""
    if latest_event_at is None:
        return Freshness.UNKNOWN
    age_days = (_as_utc(now) - _as_utc(latest_event_at)).days
    if age_days <= FRESH_MAX_DAYS:  # future timestamps (negative age) count as fresh
        return Freshness.FRESH
    if age_days <= AGING_MAX_DAYS:
        return Freshness.AGING
    return Freshness.STALE


def calculate_savings(current: Plan, alternative: Plan | None = None) -> Savings:
    """Estimated savings from cancelling (alternative=None) or switching plans."""
    currency = _clean_currency(current.currency)
    current_costs = _exact_costs(current.amount, current.billing_interval)
    if current_costs is None:
        return Savings(
            AnalysisStatus.UNSUPPORTED_CADENCE,
            detail=f"unsupported cadence: {current.billing_interval!r}",
        )

    if alternative is None:
        monthly, annual = current_costs
    else:
        if _clean_currency(alternative.currency) != currency:
            return Savings(
                AnalysisStatus.CURRENCY_MISMATCH,
                detail=f"{currency} vs {_clean_currency(alternative.currency)}; no conversion",
            )
        alt_costs = _exact_costs(alternative.amount, alternative.billing_interval)
        if alt_costs is None:
            return Savings(
                AnalysisStatus.UNSUPPORTED_CADENCE,
                detail=f"unsupported cadence: {alternative.billing_interval!r}",
            )
        monthly = current_costs[0] - alt_costs[0]
        annual = current_costs[1] - alt_costs[1]

    return Savings(
        AnalysisStatus.OK,
        monthly=Money(monthly, currency),
        annual=Money(annual, currency),
    )
