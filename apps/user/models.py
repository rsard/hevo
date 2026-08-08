from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel


class User(AbstractUser):
    """Project's user model, currently identical to Django's default AbstractUser."""

    pass


class VenueMembership(TimeStampedModel):
    """Links a user to a venue with a role; a user may belong to several venues,
    but only their active membership determines their currently managed venue."""

    class Role(models.TextChoices):
        """Roles a user can hold within a venue."""

        OWNER = 'owner', 'Proprietário'
        MANAGER = 'manager', 'Gerente'
        SALESPERSON = 'salesperson', 'Vendedor'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='venue_memberships',
    )
    venue = models.ForeignKey(
        'venue.Venue', on_delete=models.CASCADE, related_name='memberships',
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'venue')

    def __str__(self):
        return f'{self.user} @ {self.venue} ({self.role})'
