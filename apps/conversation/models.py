from django.db import models

from apps.core.models import TenantModel


class Conversation(TenantModel):
    class Channel(models.TextChoices):
        WHATSAPP = 'whatsapp', 'WhatsApp'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CLOSED = 'closed', 'Closed'

    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.WHATSAPP)
    external_contact_id = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('venue', 'channel', 'external_contact_id')

    def __str__(self):
        return f'{self.channel} - {self.external_contact_id}'


class Message(models.Model):
    class Direction(models.TextChoices):
        INBOUND = 'inbound', 'Inbound'
        OUTBOUND = 'outbound', 'Outbound'

    class SenderType(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        AI = 'ai', 'AI'
        HUMAN = 'human', 'Human'

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    direction = models.CharField(max_length=10, choices=Direction.choices)
    sender_type = models.CharField(max_length=10, choices=SenderType.choices)
    content = models.TextField()
    external_message_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['conversation', 'external_message_id'],
                condition=models.Q(external_message_id__gt=''),
                name='unique_external_message_id_per_conversation',
            ),
        ]

    def __str__(self):
        return f'{self.sender_type}: {self.content[:50]}'
