from datetime import timedelta

from django.utils import timezone

from apps.ai.services import get_provider, log_usage
from apps.conversation.models import Conversation, Message
from apps.conversation.services import ConversationService
from apps.conversation.whatsapp.client import WhatsAppClient
from apps.crm.models import Lead, LeadActivity
from apps.crm.services.crm_service import CRMService
from apps.venue.services import KnowledgeBaseService

INACTIVITY_THRESHOLD = timedelta(hours=24)
STALE_STAGES = [Lead.Stage.NEW, Lead.Stage.CONTACTED, Lead.Stage.QUALIFIED]

LOST_THRESHOLD = timedelta(days=7)
# Visit Scheduled is excluded: silence before a scheduled visit doesn't mean
# the lead is dead, and Won/Lost are terminal states we don't auto-touch.
STALE_STAGES_FOR_LOST = [
    Lead.Stage.NEW,
    Lead.Stage.CONTACTED,
    Lead.Stage.QUALIFIED,
    Lead.Stage.PROPOSAL_SENT,
    Lead.Stage.NEGOTIATION,
]

FOLLOWUP_PROMPT = (
    "The customer hasn't replied in a while. Write a short, friendly WhatsApp "
    'follow-up message in Portuguese to re-engage them, referencing their event '
    "if it's known from the conversation, without being pushy."
)


class FollowUpService:
    @staticmethod
    def leads_needing_followup(venue):
        cutoff = timezone.now() - INACTIVITY_THRESHOLD
        return Lead.objects.filter(
            venue=venue,
            stage__in=STALE_STAGES,
            last_interaction_at__lt=cutoff,
        )

    @staticmethod
    def send_followup(lead):
        conversation = lead.conversation
        context = KnowledgeBaseService.build_context(lead.venue)
        history = ConversationService.get_history(conversation)

        provider = get_provider()
        response = provider.generate(
            system_prompt=f'{context}\n\n{FOLLOWUP_PROMPT}',
            messages=history,
            temperature=0.5,
        )
        log_usage(venue=lead.venue, response=response, conversation=conversation)

        message = ConversationService.record_message(
            conversation=conversation,
            direction=Message.Direction.OUTBOUND,
            sender_type=Message.SenderType.AI,
            content=response.content,
        )
        if conversation.channel == Conversation.Channel.WHATSAPP:
            WhatsAppClient(lead.venue.whatsapp_phone_number_id).send_text(
                to=conversation.external_contact_id, body=response.content,
            )
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.AI_ACTION,
            description='Sent automated follow-up message.',
        )
        CRMService.touch_interaction(lead)
        return message

    @staticmethod
    def mark_inactive_leads_as_lost(venue):
        """A lead is only marked Lost if the customer went quiet *and* we already
        tried to re-engage them since — never just for going quiet on its own."""
        cutoff = timezone.now() - LOST_THRESHOLD
        candidates = Lead.objects.filter(venue=venue, stage__in=STALE_STAGES_FOR_LOST)
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
