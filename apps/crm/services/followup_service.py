from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.conversation.models import Conversation, Message
from apps.conversation.services import ConversationService
from apps.conversation.whatsapp.client import WhatsAppClient
from apps.crm.models import Lead, LeadActivity, Visit
from apps.crm.services.crm_service import CRMService

INACTIVITY_THRESHOLD = timedelta(hours=24)
STALE_STAGES = [Lead.Stage.NEW, Lead.Stage.CONTACTED, Lead.Stage.QUALIFIED]

LOST_THRESHOLD = timedelta(days=7)
# Won/Lost are terminal states we don't auto-touch. A lead with an upcoming
# scheduled visit is excluded separately below: silence before a visit
# doesn't mean the lead is dead, even though scheduling puts it in Negotiation.
STALE_STAGES_FOR_LOST = [
    Lead.Stage.NEW,
    Lead.Stage.CONTACTED,
    Lead.Stage.QUALIFIED,
    Lead.Stage.NEGOTIATION,
]


class FollowUpService:
    """Automates re-engaging quiet leads and marking long-silent ones as lost."""

    @staticmethod
    def leads_needing_followup(venue):
        """Returns leads in early stages with no interaction for 24h+."""
        cutoff = timezone.now() - INACTIVITY_THRESHOLD
        return Lead.objects.filter(
            venue=venue,
            stage__in=STALE_STAGES,
            last_interaction_at__lt=cutoff,
        )

    @staticmethod
    def send_followup(lead):
        """Leads eligible here have had no interaction for 24h+, which is always
        past WhatsApp's free-form customer-service window. Outside that window
        only a pre-approved template message is allowed, so this sends the
        configured template rather than AI-generated free text."""
        conversation = lead.conversation
        # Send first: a message record should only exist once we know it actually
        # went out, so a failed send doesn't show up as a phantom sent message.
        if conversation.channel == Conversation.Channel.WHATSAPP:
            WhatsAppClient(lead.venue.whatsapp_phone_number_id).send_template(
                to=conversation.external_contact_id,
                template_name=settings.WHATSAPP_FOLLOWUP_TEMPLATE_NAME,
                language_code=settings.WHATSAPP_FOLLOWUP_TEMPLATE_LANGUAGE,
            )
        message = ConversationService.record_message(
            conversation=conversation,
            direction=Message.Direction.OUTBOUND,
            sender_type=Message.SenderType.AI,
            content=settings.WHATSAPP_FOLLOWUP_TEMPLATE_TEXT,
        )
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.AI_ACTION,
            description='Follow-up automático enviado ao cliente.',
        )
        CRMService.touch_interaction(lead)
        return message

    @staticmethod
    def mark_inactive_leads_as_lost(venue):
        """A lead is only marked Lost if the customer went quiet *and* we already
        tried to re-engage them since — never just for going quiet on its own."""
        cutoff = timezone.now() - LOST_THRESHOLD
        candidates = Lead.objects.filter(venue=venue, stage__in=STALE_STAGES_FOR_LOST).exclude(
            visits__status__in=[Visit.Status.SCHEDULED, Visit.Status.CONFIRMED],
            visits__scheduled_at__gte=timezone.now(),
        )
        for lead in candidates:
            last_inbound = lead.conversation.messages.filter(
                direction=Message.Direction.INBOUND,
            ).order_by('-created_at').first()
            if last_inbound is None or last_inbound.created_at > cutoff:
                continue

            followed_up_since = lead.conversation.messages.filter(
                direction=Message.Direction.OUTBOUND, created_at__gt=last_inbound.created_at,
            ).exists()
            if not followed_up_since:
                continue

            CRMService.update_stage(lead=lead, stage=Lead.Stage.LOST)
            CRMService.log_activity(
                lead=lead,
                activity_type=LeadActivity.ActivityType.AI_ACTION,
                description=(
                    f'Marcado como perdido automaticamente: sem resposta do cliente '
                    f'há mais de {LOST_THRESHOLD.days} dias, apesar de follow-up enviado.'
                ),
            )
