"""Settings for production deployments."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, SECRET_KEY, env

if SECRET_KEY == "django-insecure-change-me-in-production":
    raise ImproperlyConfigured("SECRET_KEY must be set via environment in production.")

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")

MIDDLEWARE = list(MIDDLEWARE)
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

STORAGES = {
    "default": {"BACKEND": "storages.backends.s3.S3Storage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"
