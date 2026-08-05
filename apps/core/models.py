from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantModel(TimeStampedModel):
    venue = models.ForeignKey(
        'venue.Venue', on_delete=models.CASCADE, related_name='%(class)s_set',
    )

    class Meta:
        abstract = True
