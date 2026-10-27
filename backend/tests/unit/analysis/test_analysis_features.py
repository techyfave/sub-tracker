import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.analysis.features import (
    AnalysisStatus,
    Freshness,
    UsageLevel,
    calculate_savings,
    charges_per_year,
    classify_usage,
    evidence_freshness,
    is_positive_saving,
    normalize_cost,
)
from app.domain.common.money import Money
from app.domain.subscriptions.entities import BillingCadence, Plan


def ngn(value: str) -> Money:
    return Money(Decimal(value), "NGN")


def make_plan(amount: str, cadence: BillingCadence, currency: str = "NGN") -> Plan:
    return Plan(
        provider_id=uuid.uuid4(),
        name="test plan",
        amount=Decimal(amount),
        currency=currency,
        billing_interval=cadence,
    )


# ---------- Golden tests: answers verified by hand ----------
@pytest.mark.parametrize(
    ("amount", "cadence", "monthly", "annual"),
    [
        ("5000.00", BillingCadence.MONTHLY, "5000.00", "60000.00"),
        ("120000.00", BillingCadence.YEARLY, "10000.00", "120000.00"),
        ("5.00", BillingCadence.WEEKLY, "21.67", "260.00"),  # 5*52/12 = 21.666...
        ("1.00", BillingCadence.DAILY, "30.42", "365.00"),  # 365/12 = 30.416...
    ],
)
def test_normalize_cost_golden(amount, cadence, monthly, annual):
    result = normalize_cost(Decimal(amount), "NGN", cadence)
    assert result.status == AnalysisStatus.OK
    assert result.monthly == ngn(monthly)
    assert result.annual == ngn(annual)


def test_savings_cancel_is_full_cost():
    result = calculate_savings(make_plan("5000.00", BillingCadence.MONTHLY))
    assert result.status == AnalysisStatus.OK
    assert result.monthly == ngn("5000.00")
    assert result.annual == ngn("60000.00")


def test_savings_downgrade_same_cadence():
    current = make_plan("5000.00", BillingCadence.MONTHLY)
    cheaper = make_plan("3000.00", BillingCadence.MONTHLY)
    result = calculate_savings(current, cheaper)
    assert result.monthly == ngn("2000.00")
    assert result.annual == ngn("24000.00")


def test_savings_across_cadences():
    current = make_plan("120000.00", BillingCadence.YEARLY)  # 10000/month
    alternative = make_plan("9000.00", BillingCadence.MONTHLY)
    result = calculate_savings(current, alternative)
    assert result.monthly == ngn("1000.00")
    assert result.annual == ngn("12000.00")


# ---------- Edge cases ----------
def test_unsupported_cadence_is_explicit():
    result = normalize_cost(Decimal("5.00"), "NGN", "fortnightly")
    assert result.status == AnalysisStatus.UNSUPPORTED_CADENCE
    assert result.monthly is None
    assert charges_per_year("fortnightly") is None


def test_currency_mismatch_is_explicit():
    current = make_plan("5000.00", BillingCadence.MONTHLY, "NGN")
    alternative = make_plan("5.00", BillingCadence.MONTHLY, "USD")
    result = calculate_savings(current, alternative)
    assert result.status == AnalysisStatus.CURRENCY_MISMATCH
    assert result.monthly is None


def test_currency_comparison_ignores_case_and_spaces():
    current = make_plan("5000.00", BillingCadence.MONTHLY, "ngn")
    alternative = make_plan("3000.00", BillingCadence.MONTHLY, " NGN ")
    assert calculate_savings(current, alternative).status == AnalysisStatus.OK


def test_zero_price():
    result = normalize_cost(Decimal("0.00"), "NGN", BillingCadence.MONTHLY)
    assert result.monthly == ngn("0.00")


def test_alternative_more_expensive_gives_negative_savings():
    current = make_plan("3000.00", BillingCadence.MONTHLY)
    pricier = make_plan("5000.00", BillingCadence.MONTHLY)
    assert calculate_savings(current, pricier).monthly == ngn("-2000.00")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("2.345", "2.34"), ("2.355", "2.36")],  # half-even: ties go to the even digit
)
def test_rounding_is_half_even(raw, expected):
    result = normalize_cost(Decimal(raw), "NGN", BillingCadence.MONTHLY)
    assert result.monthly == ngn(expected)


def test_round_only_at_the_end():
    # Weekly 5.00: annual must be 260.00, not 21.67 * 12 = 260.04
    result = normalize_cost(Decimal("5.00"), "NGN", BillingCadence.WEEKLY)
    assert result.annual == ngn("260.00")


# ---------- Unknown usage is never zero ----------
def test_unknown_usage_is_not_zero():
    assert classify_usage(None) == UsageLevel.UNKNOWN
    assert classify_usage(None) != classify_usage(0)
    assert classify_usage(0) == UsageLevel.UNUSED
    assert classify_usage(3) == UsageLevel.USED


def test_negative_usage_rejected():
    with pytest.raises(ValueError):
        classify_usage(-1)


# ---------- Freshness ----------
NOW = datetime(2026, 10, 19, tzinfo=UTC)


@pytest.mark.parametrize(
    ("days_old", "expected"),
    [
        (0, Freshness.FRESH),
        (30, Freshness.FRESH),
        (31, Freshness.AGING),
        (90, Freshness.AGING),
        (91, Freshness.STALE),
    ],
)
def test_freshness_boundaries(days_old, expected):
    assert evidence_freshness(NOW - timedelta(days=days_old), NOW) == expected


def test_freshness_unknown_when_no_evidence():
    assert evidence_freshness(None, NOW) == Freshness.UNKNOWN


def test_freshness_treats_naive_datetime_as_utc():
    naive = datetime(2026, 10, 18)  # no timezone
    assert evidence_freshness(naive, NOW) == Freshness.FRESH


def test_future_evidence_counts_as_fresh():
    assert evidence_freshness(NOW + timedelta(days=2), NOW) == Freshness.FRESH


def test_fractional_saving_is_positive_annually_but_zero_monthly():
    current = make_plan("100.02", BillingCadence.YEARLY)
    alternative = make_plan("100.01", BillingCadence.YEARLY)
    result = calculate_savings(current, alternative)
    assert result.monthly == ngn("0.00")
    assert result.annual == ngn("0.01")
    assert is_positive_saving(result)


def test_is_positive_saving_false_when_not_a_saving():
    same = calculate_savings(
        make_plan("100.00", BillingCadence.YEARLY), make_plan("100.00", BillingCadence.YEARLY)
    )
    pricier = calculate_savings(
        make_plan("3000.00", BillingCadence.MONTHLY), make_plan("5000.00", BillingCadence.MONTHLY)
    )
    mismatch = calculate_savings(
        make_plan("5000.00", BillingCadence.MONTHLY, "NGN"),
        make_plan("5.00", BillingCadence.MONTHLY, "USD"),
    )
    assert not is_positive_saving(same)
    assert not is_positive_saving(pricier)
    assert not is_positive_saving(mismatch)
