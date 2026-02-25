#!/bin/sh
set -e

echo "[startup] Running migrations..."
python manage.py migrate --noinput

echo "[startup] Syncing tax rates..."
python manage.py sync_tax_rates

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
  echo "[startup] Ensuring admin user exists..."
  python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ["DJANGO_SUPERUSER_USERNAME"]
email = os.environ["DJANGO_SUPERUSER_EMAIL"]
password = os.environ["DJANGO_SUPERUSER_PASSWORD"]

user, created = User.objects.get_or_create(
    username=username,
    defaults={"email": email, "is_staff": True, "is_superuser": True},
)
if created:
    user.set_password(password)
    user.save()
    print("[startup] Admin user created.")
else:
    print("[startup] Admin user already exists.")
PY
fi

echo "[startup] Collecting static files..."
python manage.py collectstatic --noinput

echo "[startup] Starting gunicorn..."
exec gunicorn --bind=0.0.0.0:${PORT:-8000} tax_calculator.wsgi
