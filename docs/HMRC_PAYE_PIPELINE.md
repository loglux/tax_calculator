# HMRC PAYE Pipeline Methodology (`hmrc_paye`)

## Purpose
The calculator now uses `hmrc_paye` as the single calculation pipeline.

API clients can pass:

```json
{
  "calculation_mode": "hmrc_paye"
}
```

## Inputs for `hmrc_paye`
- `income`: gross input amount
- `income_type`: `yearly` or `hourly`
- `workweek_hours`: used for annualization and hourly breakdown
- `is_scotland`: selects Scotland vs rUK tax bands
- `no_ni`: disables NI calculation if `true`
- `is_blind`: adds blind allowance on top of tax-code allowance
- `tax_code`: e.g. `1257L`, `0T`, `K500`
- `payroll_frequency`: `monthly`, `weekly`, or `annual`
- `hmrc_basis`: `cumulative` or non-cumulative (week1/month1-like behavior)
- `period_number`: current payroll period index
- `ytd_tax_paid`: tax already withheld before current period (for cumulative mode)
- `ytd_gross`: gross already paid before current period (for cumulative mode)

## Calculation Steps
1. Convert input to annual salary:
   - `yearly`: salary = income
   - `hourly`: salary = income × workweek_hours × 52
2. Convert annual salary to current period gross using `payroll_frequency`.
3. Parse tax code into annual allowance:
   - normal code: digits × 10 (e.g. `1257L` → `12570`)
   - `K` code: negative digits × 10 (e.g. `K500` → `-5000`)
   - `M/N` suffix applies marriage allowance transfer (+/- 1260)
   - `NT/BR/D0/D1` are handled as special-rate codes
   - `S/C` prefix controls Scotland/rUK region for HMRC bands
   - `W1/M1/X` markers force non-cumulative basis
4. If `is_blind=true`, add blind allowance constant.
5. Compute period tax:
   - `cumulative`: tax on taxable pay-to-date minus `ytd_tax_paid`
   - non-cumulative: tax only for current period
   - use Scotland or rUK band logic with thresholds scaled by period fraction
6. Compute period NI from period gross and NI thresholds/rates.
7. Build annualized outputs for UI compatibility and expose period-specific HMRC fields.

## Returned HMRC-Specific Fields
- `hmrc_period_tax`
- `hmrc_period_ni`
- `hmrc_period_take_home`
- `hmrc_period_gross`
- `hmrc_tax_code`
- `hmrc_basis`
- `hmrc_payroll_frequency`

## Compatibility Notes
- Existing response keys (`tax_paid`, `ni_paid`, `take_home`, etc.) are still returned.
- In `hmrc_paye`, those main totals are annualized estimates derived from period calculations.

## Current Limitations
- This is a PAYE-oriented approximation, not a full HMRC engine clone.
- Scotland advanced/top split depends on available model fields.
- Tax-code edge cases (full HMRC coding rules) are not fully modeled yet.

## Tax Rate Data Management
Tax rates are centralized in:

- `calculator/tax_rate_seed_data.py`

Use management command to sync DB safely (upsert by `year`):

```bash
./.venv/bin/python manage.py sync_tax_rates --dry-run
./.venv/bin/python manage.py sync_tax_rates
```

The command prints source links and updates/creates rows for supported tax years.

## Reference Vectors
Regression vectors for HMRC mode are stored in:

- `calculator/reference_vectors/hmrc_paye_2025.json`

They are validated by:

- `calculator/test_hmrc_reference_vectors.py`

## Suggested Next Enhancements
1. Store all allowances/bands/rates by tax year (including blind allowance and full Scotland set).
2. Add explicit week1/month1 handling flags and tests against known HMRC examples.
3. Add tax-code parser support for additional suffix/prefix rules.
4. Add regression test vectors for boundary thresholds and cumulative transitions.

## Authoritative References
Use these pages as the source of truth for implementation details and yearly values:

- PAYE cumulative basis and period logic (HMRC PAYE Manual, PAYE70025):  
  https://www.gov.uk/hmrc-internal-manuals/paye-manual/paye70025
- Tax code construction rules, including edge cases (`K` codes and coding structure):  
  https://www.gov.uk/hmrc-internal-manuals/paye-manual/paye11065  
  https://www.gov.uk/hmrc-internal-manuals/paye-manual/paye11095
- NI exact percentage method and rounding to nearest penny:  
  https://www.gov.uk/hmrc-internal-manuals/national-insurance-manual/nim11002
- NI tables method (weekly £1 bands, monthly £4 bands, next-lower table value):  
  https://www.gov.uk/hmrc-internal-manuals/national-insurance-manual/nim11003
- Income Tax current rates/allowances and Personal Allowance taper rule:  
  https://www.gov.uk/income-tax-rates
- HMRC publication with current and previous Income Tax rates and allowances (including Scotland table):  
  https://www.gov.uk/government/publications/rates-and-allowances-income-tax/income-tax-rates-and-allowances-current-and-past
- Scotland Income Tax overview and links to current bands/rates:  
  https://www.gov.uk/scottish-income-tax
- Blind Person’s Allowance current guidance and amount:  
  https://www.gov.uk/blind-persons-allowance/what-youll-get
