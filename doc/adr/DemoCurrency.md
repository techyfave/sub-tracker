
The MVP requires monetary values for demo and seed data. The application needs one predictable currency for development, testing, and demonstrations while avoiding unnecessary multi-currency complexity during the MVP.

Because the initial target environment is Nigeria, the canonical demo currency should be the Nigerian Naira.

The domain should nevertheless represent currency explicitly so that USD and other currencies can be introduced later without redesigning the monetary model.

## Decision

The MVP uses **Nigerian Naira (NGN / ₦)** as the canonical demo currency.

All seed and demo monetary values MUST use NGN unless a specific test or integration explicitly requires another currency.

Currency must be represented as a domain value and must not be hard-coded into presentation logic.

For example:

```json
{
  "amount": 15000,
  "currency": "NGN"
}
```

The currency code should use the **ISO 4217** representation:

* `NGN` — Nigerian Naira
* `USD` — United States Dollar
* Other currencies should use their appropriate ISO 4217 code.

---

## Currency Conditions

### Condition 1 — Default/MVP currency

If no currency is explicitly supplied for demo or seed data:

```text
currency = NGN
```

Therefore, all normal MVP seed records use NGN.

Example:

```json
{
  "amount": 25000,
  "currency": "NGN"
}
```

---

### Condition 2 — USD

USD may be used when the data explicitly represents a USD-denominated transaction, external integration, or test case.

Example:

```json
{
  "amount": 100,
  "currency": "USD"
}
```

The system MUST NOT automatically treat USD values as NGN or convert USD to NGN unless currency conversion has been explicitly implemented.

---

### Condition 3 — Other currencies

Other currencies may be represented when required by an integration, test, or future feature.

Example:

```json
{
  "amount": 500,
  "currency": "EUR"
}
```

The backend should preserve the supplied currency rather than silently converting it.

Supported currencies should eventually be controlled through a defined currency list/enum rather than accepting arbitrary strings.

---

### Condition 4 — Currency conversion

The MVP does **not** perform automatic currency conversion.

For example, the system must not automatically convert:

```text
USD → NGN
EUR → NGN
GBP → NGN
```

unless an explicit currency-conversion feature and exchange-rate source are introduced.

This prevents exchange-rate assumptions from affecting financial or demo data.

---

### Condition 5 — API responses

API responses containing monetary values should return both the numeric amount and currency.

Preferred:

```json
{
  "amount": 15000,
  "currency": "NGN"
}
```

Avoid:

```json
{
  "amount": "₦15,000"
}
```

Formatting such as `₦15,000` belongs to the presentation/frontend layer.

---

## Consequences

### Positive

* NGN provides a locally appropriate default for the MVP.
* Seed data remains deterministic.
* API consumers always know which currency an amount represents.
* USD and other currencies can be represented without changing the monetary structure.
* Currency formatting remains separate from domain logic.
* Future multi-currency support can be introduced incrementally.
* Avoids premature exchange-rate and conversion complexity.

### Negative

* The MVP does not provide automatic currency conversion.
* Developers must explicitly specify the currency when working with non-NGN values.
* Multi-currency validation and exchange-rate handling will require additional implementation in the future.
* Existing seed data must be updated if it currently assumes USD.

---

## Example

### MVP seed data

```json
{
  "price": {
    "amount": 50000,
    "currency": "NGN"
  }
}
```

### USD-specific record

```json
{
  "price": {
    "amount": 100,
    "currency": "USD"
  }
}
```

### Other currency

```json
{
  "price": {
    "amount": 75,
    "currency": "GBP"
  }
}
```

In all three cases, the backend preserves the amount and its associated currency. Conversion and display formatting are separate concerns.

## Implementation Rule

**NGN is the default and canonical MVP demo currency.**

USD or another currency may be used only when the record explicitly requires that currency.

No component should infer or silently convert one currency into another.

If multi-currency transactions, exchange rates, or automatic conversion become an MVP requirement, this ADR must be revisited or superseded by a new ADR.
