from celery import shared_task

from apps.ai.services import get_provider, log_usage
from apps.conversation.models import Message
from apps.conversation.services import ConversationService
from apps.conversation.whatsapp.client import WhatsAppClient
from apps.crm.models import LeadActivity
from apps.crm.services import CRMService, QualificationService
from apps.venue.models import Venue
from apps.venue.services import KnowledgeBaseService

SALES_PERSONA_PROMPT = (
    "You are the AI sales assistant for {venue_name}, a wedding/event venue in Brazil. "
    "Talk to the customer in warm, natural Portuguese, like the venue's best salesperson. "
    'Answer only using the knowledge base below. Ask qualifying questions (event date, '
    'guest count, budget) naturally over the conversation, and offer to schedule a visit '
    'once the customer seems interested.\n\nKnowledge base:\n{context}'
)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_inbound_whatsapp_message(self, *, phone_number_id, from_wa_id, message_id, text):
    """Generates and sends the AI reply to an inbound WhatsApp message.

    Creates/updates the lead, skips replying if escalated to a human, and retries
    on failure via Celery. Runs qualification after a successful reply.
    """
    try:
        venue = Venue.objects.get(whatsapp_phone_number_id=phone_number_id, is_active=True)
    except Venue.DoesNotExist:
        return

    conversation = ConversationService.get_or_create_conversation(
        venue=venue, external_contact_id=from_wa_id,
    )

    inbound_message, created = ConversationService.get_or_create_inbound_message(
        conversation=conversation,
        sender_type=Message.SenderType.CUSTOMER,
        content=text,
        external_message_id=message_id,
    )
    if not created:
        already_replied = conversation.messages.filter(
            direction=Message.Direction.OUTBOUND, created_at__gte=inbound_message.created_at,
        ).exists()
        if already_replied:
            # A redelivered webhook for a message we've already fully handled.
            return

    lead = CRMService.get_or_create_lead(conversation=conversation, customer_phone=from_wa_id)
    CRMService.touch_interaction(lead)

    if lead.escalated_at:
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.NOTE,
            description='Nova mensagem recebida durante escalonamento; resposta automática pausada.',
        )
        return

    try:
        system_prompt = SALES_PERSONA_PROMPT.format(
            venue_name=venue.name, context=KnowledgeBaseService.build_context(venue),
        )
        history = ConversationService.get_history(conversation)

        provider = get_provider()
        response = provider.generate(system_prompt=system_prompt, messages=history)
        log_usage(venue=venue, response=response, conversation=conversation)

        # Send before recording: if the send raises, no outbound row exists, so a
        # retry correctly starts over instead of the already_replied check above
        # mistaking "we saved a reply" for "we actually delivered one".
        WhatsAppClient(phone_number_id).send_text(to=from_wa_id, body=response.content)
        ConversationService.record_message(
            conversation=conversation,
            direction=Message.Direction.OUTBOUND,
            sender_type=Message.SenderType.AI,
            content=response.content,
        )
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            CRMService.log_activity(
                lead=lead,
                activity_type=LeadActivity.ActivityType.AI_ACTION,
                description=f'Falha ao gerar ou enviar resposta automática: {exc}',
            )
        raise self.retry(exc=exc)

    try:
        QualificationService.qualify(lead)
    except Exception:
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.AI_ACTION,
            description='Falha ao qualificar o lead automaticamente.',
        )
