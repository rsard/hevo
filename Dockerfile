FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app


FROM base AS development

ENV DJANGO_SETTINGS_MODULE=config.settings.development

COPY requirements/ requirements/
RUN pip install -r requirements/development.txt

COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


FROM base AS production

ENV DJANGO_SETTINGS_MODULE=config.settings.production

COPY requirements/ requirements/
RUN pip install -r requirements/production.txt

COPY . .

# collectstatic only needs STATIC_ROOT/STATICFILES_DIRS, not the production
# security settings, so it runs against dev settings to avoid requiring a
# real SECRET_KEY/ALLOWED_HOSTS at build time. DATABASE_URL isn't used here
# either, but settings.py requires it to be parseable just to import.
RUN DJANGO_SETTINGS_MODULE=config.settings.development \
    DATABASE_URL=postgres://build:build@localhost/build \
    python manage.py collectstatic --noinput \
    && chown -R app:app /app

USER app

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
