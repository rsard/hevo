from django.db import models

from apps.core.models import TimeStampedModel


class Subscription(TimeStampedModel):
    """A venue's billing plan and subscription status."""

    class Status(models.TextChoices):
        TRIALING = "trialing", "Em teste"
        ACTIVE = "active", "Ativa"
        PAST_DUE = "past_due", "Pagamento pendente"
        CANCELED = "canceled", "Cancelada"

    venue = models.OneToOneField(
        "venue.Venue", on_delete=models.CASCADE, related_name="subscription",
    )
    plan_name = models.CharField(max_length=100)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIALING)
    started_at = models.DateField()
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.venue} - {self.get_status_display()}"
