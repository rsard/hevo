from django.conf import settings
from django.db import models

from apps.core.fields import EncryptedTextField
from apps.core.models import TenantModel, TimeStampedModel


class Label(TenantModel):
    """A colored tag venues can attach to leads for organization."""

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
    """A prospective customer conversation tracked through the sales funnel."""

    class Stage(models.TextChoices):
        NEW = 'new', 'Novo Lead'
        CONTACTED = 'contacted', 'Contatado'
        QUALIFIED = 'qualified', 'Qualificado'
        NEGOTIATION = 'negotiation', 'Em Negociação'
        WON = 'won', 'Concluído'
        LOST = 'lost', 'Arquivado'

    class Sentiment(models.TextChoices):
        POSITIVE = 'positive', 'Positivo'
        NEUTRAL = 'neutral', 'Neutro'
        NEGATIVE = 'negative', 'Negativo'

    class Urgency(models.TextChoices):
        LOW = 'low', 'Baixa'
        MEDIUM = 'medium', 'Média'
        HIGH = 'high', 'Alta'
        URGENT = 'urgent', 'Urgente'

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
    urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.MEDIUM)
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
    """An audit log entry recording a note, stage change, or action on a lead."""

    class ActivityType(models.TextChoices):
        NOTE = 'note', 'Nota'
        STAGE_CHANGE = 'stage_change', 'Mudança de Estágio'
        AI_ACTION = 'ai_action', 'Ação da IA'
        HUMAN_ACTION = 'human_action', 'Ação Humana'
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
    """A scheduled venue visit for a lead, optionally synced to an external calendar."""

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Agendada'
        CONFIRMED = 'confirmed', 'Confirmada'
        COMPLETED = 'completed', 'Concluída'
        CANCELLED = 'cancelled', 'Cancelada'
        NO_SHOW = 'no_show', 'Não Compareceu'

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
    """Stores a venue's OAuth connection to an external calendar provider."""

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


class EmailLog(TenantModel):
    """Records a single outbound email, so we can monitor usage against the
    SMTP provider's daily sending limit."""

    subject = models.CharField(max_length=255, blank=True)
    recipient_count = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.subject} - {self.venue}'
