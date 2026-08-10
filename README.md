# Hevo

AI sales agent for wedding and event venues. Hevo qualifies inbound WhatsApp
leads automatically, tracks them through a sales pipeline, schedules visits
against Google Calendar, and gives venue staff a dashboard to manage it all —
built HTMX-first with minimal JavaScript.

## Stack

- Django 6 (Python 3.12)
- PostgreSQL, Redis
- Celery + Celery Beat for background/scheduled work
- HTMX for interactivity, no frontend framework
- OpenAI for lead qualification, Google Calendar API for scheduling

## Features

- **WhatsApp qualification** — inbound messages are parsed and scored by an
  LLM in a single call (event details, sentiment, negotiation signals), which
  drives automatic stage transitions on the lead.
- **Human escalation** — when a customer asks to talk to a person, automatic
  replies pause and staff get an alert.
- **CRM kanban** — leads grouped by stage, with staleness/escalation alerts,
  manual labels, and private internal notes.
- **Dashboard** — conversion funnel, weekly reports, and pipeline stats.
- **Calendar** — Google Calendar OAuth connection with a dedicated agenda view.
- **Backoffice** — admin-only screen for provisioning new customer accounts
  (signup isn't self-serve).

## Local development

### Option A: Docker Compose (recommended)

```bash
cp .env.example .env   # fill in real values as needed
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

The app is served at http://localhost:8000. `docker compose up` also starts
Postgres, Redis, a Celery worker, and Celery beat. The `web` service bind-mounts
the repo, so code changes reload automatically.

### Option B: Local virtualenv

Requires a local PostgreSQL and Redis.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements/development.txt
cp .env.example .env   # point DATABASE_URL/REDIS_URL at your local services
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Run Celery separately when you need background tasks:

```bash
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info
```

### Linting and tests

```bash
ruff check .
python manage.py test
```

## Settings

Settings are split by environment under `config/settings/`:

- `base.py` — shared configuration
- `development.py` — permissive defaults for local work (`DEBUG=True`)
- `production.py` — enforces `SECRET_KEY`/`ALLOWED_HOSTS` from the
  environment (fails fast if missing), HTTPS/HSTS, secure cookies, and
  WhiteNoise for static files

Select one via `DJANGO_SETTINGS_MODULE` (defaults to `config.settings.development`
for `manage.py`/`wsgi`/`asgi`/`celery`). See `.env.example` for all supported
environment variables.

## Docker images

The `Dockerfile` has two build targets:

```bash
docker build --target development -t hevo:development .
docker build --target production -t hevo:production .
```

`development` runs `manage.py runserver`. `production` runs `gunicorn` behind
a non-root user, with static files pre-collected at build time.

## CI

GitHub Actions runs on every push to `main` and on pull requests:

- `.github/workflows/ci.yml` — lint (ruff), Django system check, migration
  drift check, and the test suite, against real Postgres/Redis services
- `.github/workflows/docker.yml` — builds both Docker targets to catch
  Dockerfile breakage

## Deploy

Dev and prod each run on a single EC2 instance via Docker Compose, with
automatic deploy from GitHub Actions on push to `develop`/`main`. See
[`docs/DEPLOY.md`](docs/DEPLOY.md) for the full setup runbook and
[`deploy/`](deploy) for the server-side Compose/Caddy files.

## Project layout

```
apps/
  ai/            LLM provider abstraction
  backoffice/    admin-only customer provisioning
  conversation/  WhatsApp webhook, message parsing, inbound processing
  core/          shared base models/mixins (tenancy, encrypted fields)
  crm/           leads, kanban, labels, notes, escalation, calendar/agenda
  dashboard/     charts and pipeline stats
  user/          auth, venue membership
  venue/         venue profile, menu, packages, FAQs, opening hours
config/          Django project settings/urls/wsgi/asgi/celery app
```
