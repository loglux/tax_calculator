# UK Tax & NI Calculator

Web app and API for UK PAYE-style tax and National Insurance calculations.

Live demo: `https://tax.log7.uk/calculator/`

## Current State
- HMRC-oriented pipeline is the default and only calculation mode in UI/API.
- Supports Scotland/rUK behavior via flags and tax-code prefixes (`S`/`C`).
- API is protected with JWT bearer token.
- Tax rates are stored in DB and synced from seed data.

## Quick Start (Local)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py sync_tax_rates
python manage.py runserver
```

Open:
- `http://127.0.0.1:8000/calculator/`

## API Authentication
Get JWT token:
```bash
curl -X POST http://127.0.0.1:8000/calculator/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR_USER","password":"YOUR_PASSWORD"}'
```

Use token:
```bash
curl -X POST http://127.0.0.1:8000/calculator/api/calculate/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "tax_year": 2025,
        "income": 60000,
        "income_type": "yearly",
        "workweek_hours": 40,
        "tax_code": "1257L",
        "is_blind": false,
        "no_ni": false,
        "mca": false,
        "is_scotland": false
      }'
```

## Notes
- This is not an official HMRC service.
- Use results for demonstration/planning, not as legal tax advice.
- Do not commit local DB or secret files (`db.sqlite3`, `.env`).
