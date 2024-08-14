FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app/
COPY settings_docker.py /app/tax_calculator/settings_docker.py

ENV DJANGO_SETTINGS_MODULE=tax_calculator.settings_docker

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "tax_calculator.wsgi:application", "--bind", "0.0.0.0:8000"]
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
