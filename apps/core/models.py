from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base adding created_at/updated_at timestamps to a model."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantModel(TimeStampedModel):
    """Abstract base for models scoped to a single venue (multi-tenant data).

    Subclasses get a venue FK plus timestamps; callers are expected to filter
    querysets by venue themselves (see VenueScopedViewMixin) since this base
    has no default manager enforcing the scoping."""

    venue = models.ForeignKey(
        "venue.Venue", on_delete=models.CASCADE, related_name="%(class)s_set",
    )

    class Meta:
        abstract = True
