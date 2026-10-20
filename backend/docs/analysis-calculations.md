# Analysis calculations: rounding and conventions

- All money math uses `Decimal`, never `float`.
- Rounding happens ONCE, when a `Money` value is created. It rounds to 2 decimal
  places using `ROUND_HALF_EVEN` (banker's rounding), as defined in
  `app/domain/common/money.py`. Example: 2.345 -> 2.34 and 2.355 -> 2.36.
- Monthly and annual figures are each computed from the exact, unrounded price,
  never from each other. (Weekly 5.00: annual = 5 x 52 = 260.00, not 21.67 x 12.)
- Charges per year: daily 365, weekly 52, monthly 12, yearly 1.
  Monthly cost = annual cost / 12.
- Savings are estimates. Savings = current cost - alternative cost, or the full
  current cost for a cancellation. Negative means the alternative costs more.
- Different currencies are never converted (ADR-005); the result is
  `currency_mismatch`.
- Unknown usage (`None`) is never treated as zero usage.
- Freshness thresholds: <= 30 days fresh, <= 90 days aging, otherwise stale.

## Downgrade eligibility and precision

The worker uses `calculate_savings` with domain `Plan`/`BillingCadence` inputs.
It compares exact annual costs for eligibility and persists the returned monthly
and annual differences, each independently rounded once. For example, yearly
120.07 minus yearly 100.01 produces monthly 1.67 and annual 20.06. The annual
figure must never be inferred by multiplying the rounded monthly figure by 12.

A cheaper plan whose positive annual saving is representable to cents is allowed
even if its monthly equivalent rounds to zero (yearly 100.02 minus 100.01 gives
monthly 0.00 and annual 0.01). A positive annual gain that itself rounds to 0.00
is rejected as `savings_below_precision`; equal or more expensive alternatives
are rejected as `alternative_not_cheaper`. Unsupported cadences or currencies
fail validation rather than creating a recommendation.
