from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel


class User(AbstractUser):
    pass


class VenueMembership(TimeStampedModel):
    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        MANAGER = 'manager', 'Manager'
        SALESPERSON = 'salesperson', 'Salesperson'

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
