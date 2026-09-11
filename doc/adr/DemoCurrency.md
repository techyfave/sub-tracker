The MVP requires monetary values for demo and seed data. The application needs one predictable currency for development, testing, and demonstrations while avoiding unnecessary multi-currency complexity during the MVP.Because the initial target environment is Nigeria, the canonical demo currency should be the Nigerian Naira.

The domain should nevertheless represent currency explicitly so that USD and other currencies can be introduced later without redesigning the monetary model.

1. **NGN as the main demo currency**
   - Matches the MVP demo context.
   - Provides one deterministic currency for seed data.

2. **USD as the optional demo currency for international audience**
   - Familiar in many software examples.
   - Does not match the MVP's Nigerian demo context.

3. **Allow seed data to mix currencies without a canonical value**
   - More realistic in some datasets.
   - Makes deterministic demos and calculations ambiguous.

## Decision

The main demo/seed currency is **NGN (Nigerian Naira)**.

All monetary values in deterministic seed data use `NGN`.

The domain stores currency explicitly with every Money value:

```text
Money
- amount_minor
- currency
```

`amount_minor` is an integer in the currency's minor unit. The application must not use floating-point values for persisted monetary amounts.

USD and other currencies are permitted when representing a real source record that is actually denominated in that currency. The system must:

- preserve the source currency;
- never silently label a non-NGN amount as NGN;
- never perform implicit currency conversion;
- require an explicit exchange-rate/conversion operation if a cross-currency comparison is introduced later.

## Consequences

### Positive

- Seed/demo behavior is deterministic and locally relevant.
- Currency ambiguity is removed from the MVP.
- Real external subscriptions can still preserve their original currencies.
- Money handling is explicit and safer.

## Multi-currency 

- option will be determine by the team.
