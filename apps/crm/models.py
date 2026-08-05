from django.conf import settings
from django.db import models

from apps.core.fields import EncryptedTextField
from apps.core.models import TenantModel, TimeStampedModel


class Label(TenantModel):
    class Color(models.TextChoices):
        BLUE = 'blue', 'Azul'
        GREEN = 'green', 'Verde'
        MAGENTA = 'magenta', 'Magenta'
        YELLOW = 'yellow', 'Amarelo'
        AQUA = 'aqua', 'Água'
        ORANGE = 'orange', 'Laranja'
        VIOLET = 'violet', 'Violeta'
        RED = 'red', 'Vermelho'

    name = models.CharField(max_length=50)
    color = models.CharField(max_length=10, choices=Color.choices, default=Color.BLUE)

    class Meta:
        unique_together = ('venue', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class Lead(TenantModel):
    class Stage(models.TextChoices):
        NEW = 'new', 'New Lead'
        CONTACTED = 'contacted', 'Contacted'
        QUALIFIED = 'qualified', 'Qualified'
        VISIT_SCHEDULED = 'visit_scheduled', 'Visit Scheduled'
        PROPOSAL_SENT = 'proposal_sent', 'Proposal Sent'
        NEGOTIATION = 'negotiation', 'Negotiation'
        WON = 'won', 'Won'
        LOST = 'lost', 'Lost'

    class Sentiment(models.TextChoices):
        POSITIVE = 'positive', 'Positive'
        NEUTRAL = 'neutral', 'Neutral'
        NEGATIVE = 'negative', 'Negative'

    conversation = models.OneToOneField(
        'conversation.Conversation', on_delete=models.CASCADE, related_name='lead',
    )
    customer_name = models.CharField(max_length=255, blank=True)
    customer_phone = models.CharField(max_length=20)
    event_type = models.ForeignKey(
        'venue.EventType', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads',
    )
    event_date = models.DateField(null=True, blank=True)
    guest_count = models.PositiveIntegerField(null=True, blank=True)
    estimated_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    conversation_summary = models.TextField(blank=True)
    qualification_score = models.PositiveSmallIntegerField(null=True, blank=True)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.NEW)
    sentiment = models.CharField(max_length=10, choices=Sentiment.choices, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads',
    )
    last_interaction_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    labels = models.ManyToManyField(Label, blank=True, related_name='leads')

    def __str__(self):
        return self.customer_name or self.customer_phone


class LeadActivity(models.Model):
    class ActivityType(models.TextChoices):
        NOTE = 'note', 'Note'
        STAGE_CHANGE = 'stage_change', 'Stage Change'
        AI_ACTION = 'ai_action', 'AI Action'
        HUMAN_ACTION = 'human_action', 'Human Action'
        ESCALATION = 'escalation', 'Escalonamento'

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    description = models.TextField()
    from_stage = models.CharField(max_length=20, choices=Lead.Stage.choices, blank=True)
    to_stage = models.CharField(max_length=20, choices=Lead.Stage.choices, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'lead activities'

    def __str__(self):
        return f'{self.get_activity_type_display()} - {self.lead}'


class Visit(TenantModel):
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        CONFIRMED = 'confirmed', 'Confirmed'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No Show'

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='visits')
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    calendar_event_id = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['scheduled_at']

    def __str__(self):
        return f'{self.lead} - {self.scheduled_at}'


class CalendarConnection(TimeStampedModel):
    class Provider(models.TextChoices):
        GOOGLE = 'google', 'Google Calendar'

    venue = models.OneToOneField(
        'venue.Venue', on_delete=models.CASCADE, related_name='calendar_connection',
    )
    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.GOOGLE)
    calendar_id = models.CharField(max_length=255)
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField()
    token_expires_at = models.DateTimeField()

    def __str__(self):
        return f'{self.venue} - {self.get_provider_display()}'
