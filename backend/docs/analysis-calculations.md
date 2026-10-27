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
- Positive-saving policy (`is_positive_saving`): the calculation succeeded, the annual
  amount is above zero, and the monthly amount is not negative. A tiny saving can round to
  0.00 per month and still be a real 0.01 per year. Annual savings come from the exact
  prices, never from the rounded monthly figure. The contract validator and the analysis
  worker must both use this function.
