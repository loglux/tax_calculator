# Tax Rate Data Validation (2024/25 to 2026/27)

Last reviewed: 2026-02-25

## Scope
- Tax years in app DB: `2024` (2024/25), `2025` (2025/26), `2026` (2026/27)
- Fields reviewed:
  - rUK income tax thresholds/rates
  - Scotland thresholds/rates
  - NI employee thresholds/rates (PT/UEL/main/additional)
  - Personal Allowance, Blind Person's Allowance, Married Couple's Allowance max relief

## Primary sources used
- HMRC PAYE rates and thresholds (2024/25):  
  https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2024-to-2025
- HMRC PAYE rates and thresholds (2025/26):  
  https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2025-to-2026
- HMRC PAYE rates and thresholds (2026/27):  
  https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027
- HMRC rates and allowances (current and past tax years):  
  https://www.gov.uk/government/publications/rates-and-allowances-income-tax/rates-and-allowances-income-tax
- Autumn Budget 2024 Annex A (2026/27 allowances and NI):  
  https://www.gov.uk/government/publications/autumn-budget-2024/autumn-budget-2024-html#annex-a-rates-and-allowances
- Scottish Government income tax policy note (2026/27 rates and bands):  
  https://www.gov.scot/publications/scottish-income-tax-policy-note/pages/3/

## Validation result summary
- `2024/25`: mostly correct in DB seed; one mismatch found.
- `2025/26`: mostly correct in DB seed; one mismatch found.
- `2026/27`: values align with current sources used in project.

## Mismatch found and fixed
- Field: `advanced_threshold_scotland`
- Affected years: `2024`, `2025`
- Previous value: `112570.00`
- Correct value (HMRC PAYE threshold basis): `125140.00`

This fix is implemented in:
- `calculator/tax_rate_seed_data.py`
- data migration `calculator/migrations/0010_fix_scotland_advanced_thresholds.py`

## Notes
- Some headline rates/thresholds are intentionally unchanged between consecutive years, so equal take-home across years can be expected for many input scenarios.
- Differences are still present in allowances and Scottish band cutoffs by year; impact depends on income level, region, and flags.
