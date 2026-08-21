from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.conversation.models import Conversation, Message
from apps.conversation.services import ConversationService
from apps.conversation.whatsapp.client import WhatsAppClient
from apps.crm.models import LeadActivity, Visit
from apps.crm.services.crm_service import CRMService


class ReminderService:
    """Sends an automated WhatsApp reminder ahead of a lead's scheduled visit,
    to cut down on no-shows."""

    @staticmethod
    def visits_needing_reminder(venue):
        """Visits due within the reminder window that haven't been reminded yet."""
        now = timezone.now()
        cutoff = now + timedelta(hours=settings.WHATSAPP_VISIT_REMINDER_HOURS_BEFORE)
        return Visit.objects.filter(
            venue=venue,
            status__in=[Visit.Status.SCHEDULED, Visit.Status.CONFIRMED],
            reminder_sent_at__isnull=True,
            scheduled_at__gt=now,
            scheduled_at__lte=cutoff,
        )

    @staticmethod
    def send_reminder(visit):
        """Sends the reminder template and marks the visit so it isn't sent twice.

        Visit reminders typically fire well outside the 24h customer-service
        window (visits are often booked days in advance), so — like follow-ups
        — this sends the pre-approved template rather than AI-generated text."""
        lead = visit.lead
        conversation = lead.conversation
        when = timezone.localtime(visit.scheduled_at).strftime('%d/%m às %H:%M')
        content = (
            settings.WHATSAPP_VISIT_REMINDER_TEMPLATE_BODY
            .replace('{{1}}', lead.venue.name)
            .replace('{{2}}', when)
        )

        # Send first: a message record should only exist once we know it actually
        # went out, so a failed send doesn't show up as a phantom sent message.
        if conversation.channel == Conversation.Channel.WHATSAPP:
            WhatsAppClient(lead.venue.whatsapp_phone_number_id).send_template(
                to=conversation.external_contact_id,
                template_name=settings.WHATSAPP_VISIT_REMINDER_TEMPLATE_NAME,
                language_code=settings.WHATSAPP_VISIT_REMINDER_TEMPLATE_LANGUAGE,
                body_params=[lead.venue.name, when],
            )
        ConversationService.record_message(
            conversation=conversation,
            direction=Message.Direction.OUTBOUND,
            sender_type=Message.SenderType.AI,
            content=content,
        )

        visit.reminder_sent_at = timezone.now()
        visit.save(update_fields=['reminder_sent_at'])
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.AI_ACTION,
            description=f'Sent automated visit reminder for {when}.',
        )
        CRMService.touch_interaction(lead)
        return visit
