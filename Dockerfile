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

# Must run against PRODUCTION settings: that's what picks whitenoise's
# CompressedManifestStaticFilesStorage, which writes staticfiles.json. Without
# it, {% static %} 500s at runtime with "Missing staticfiles manifest entry"
# on every page, since the manifest this backend needs was never generated.
# The real SECRET_KEY/ALLOWED_HOSTS/DATABASE_URL aren't available yet at
# build time and aren't needed for collectstatic — these are just
# throwaway values that satisfy production.py's fail-fast checks.
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    SECRET_KEY=build-time-only-not-used-at-runtime \
    ALLOWED_HOSTS=localhost \
    DATABASE_URL=postgres://build:build@localhost/build \
    python manage.py collectstatic --noinput \
    && chown -R app:app /app

USER app

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
