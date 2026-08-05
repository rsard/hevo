from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


def _fernet():
    return Fernet(settings.FIELD_ENCRYPTION_KEY)


class EncryptedTextField(models.TextField):
    """Transparently encrypts at rest with Fernet. For long-lived secrets
    (OAuth refresh tokens) that would be sensitive if the database leaked."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return value
        return _fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        return _fernet().decrypt(value.encode()).decode()
