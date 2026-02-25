# Azure Secure Deployment (No DB/Passwords in GitHub)

## Goal
- Publish source code to GitHub.
- Avoid publishing local DB (`db.sqlite3`) and admin credentials.
- Keep app deployable in Azure.

## What is implemented in this repo
- `db.sqlite3` is ignored via `.gitignore`.
- GitHub Actions zip deploy excludes:
  - `db.sqlite3`, `*.sqlite3`
  - `.env`, `.env.*`
  - local/static artifacts
- `startup.sh` bootstraps runtime safely:
  - `python manage.py migrate --noinput`
  - `python manage.py sync_tax_rates`
  - optional admin auto-create from environment variables
  - `python manage.py collectstatic --noinput`
  - starts gunicorn

## Required Azure App Settings
Set these in Azure Web App Configuration:

- `SECRET_KEY` = strong random value (required)
- `DJANGO_DEBUG` = `False`
- `DJANGO_SUPERUSER_USERNAME` = admin login
- `DJANGO_SUPERUSER_EMAIL` = admin email
- `DJANGO_SUPERUSER_PASSWORD` = admin password

Then set **Startup Command** to:

```bash
bash startup.sh
```

## First secure publish checklist
1. Ensure `db.sqlite3` is not tracked in git.
2. Rotate credentials used previously in tracked DB/admin.
3. Push changes to GitHub.
4. Verify deploy logs show `migrate` + `sync_tax_rates`.
5. Login to `/admin/` using env-configured admin user.

## Important note
If `db.sqlite3` had already been pushed earlier, its contents remain in git history.
For strict cleanup, rewrite repository history (e.g. `git filter-repo`) and rotate all credentials.
