import logging

from celery import shared_task
from django.utils import timezone

from apps.ai.services import get_provider, log_usage
from apps.conversation.models import Message
from apps.conversation.services import ConversationService
from apps.conversation.whatsapp.client import WhatsAppClient
from apps.crm.models import LeadActivity
from apps.crm.services import CRMService, QualificationService
from apps.crm.tasks import send_escalation_notification
from apps.venue.models import Venue
from apps.venue.services import KnowledgeBaseService

logger = logging.getLogger(__name__)

SALES_PERSONA_PROMPT = (
    "You are the AI sales assistant for {venue_name}, a wedding/event venue in Brazil. "
    "Talk to the customer in warm, natural Portuguese, like the venue's best salesperson. "
    'Answer only using the knowledge base below. Ask qualifying questions (event date, '
    'guest count, budget) naturally over the conversation, and offer to schedule a visit '
    'once the customer seems interested. Never say you will check something and answer '
    'later — if the knowledge base includes a FATO DE DISPONIBILIDADE, state it '
    "immediately in this reply; if you're missing information needed to answer (like "
    'the event date), ask for it directly in this same reply instead of promising to '
    'get back to them.\n\nKnowledge base:\n{context}'
)

# WhatsApp message types the AI can't act on — these get escalated to a human
# instead of silently dropped.
NON_TEXT_MESSAGE_LABELS = {
    'image': 'uma imagem',
    'audio': 'um áudio',
    'video': 'um vídeo',
    'document': 'um documento',
    'sticker': 'uma figurinha',
    'location': 'uma localização',
    'contacts': 'um contato',
}

NON_TEXT_ESCALATION_ACK = (
    'Recebi o que você mandou, mas ainda não consigo abrir esse tipo de arquivo por '
    'aqui — já chamei alguém da nossa equipe pra te ajudar com isso, só um momento!'
)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_inbound_whatsapp_message(
    self, *, phone_number_id, from_wa_id, message_id, text, contact_name='',
):
    """Generates and sends the AI reply to an inbound WhatsApp message.

    Creates/updates the lead, skips replying if escalated to a human, and retries
    on failure via Celery. Qualifies the lead before generating the reply, so an
    event date just mentioned is already checked against the calendar and can be
    answered as a fact instead of a promise to check later.
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

    lead = CRMService.get_or_create_lead(
        conversation=conversation, customer_phone=from_wa_id, customer_name=contact_name,
    )
    CRMService.touch_interaction(lead)

    if lead.escalated_at:
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.NOTE,
            description='Nova mensagem recebida durante escalonamento; resposta automática pausada.',
        )
        return

    # Qualify first so a just-mentioned event date is already checked against the
    # calendar before we reply — the sales prompt states it as a fact instead of
    # promising to "check and get back to you" and never following through.
    try:
        availability_note = QualificationService.qualify(lead)
    except Exception:
        availability_note = ''
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.AI_ACTION,
            description='Falha ao qualificar o lead automaticamente.',
        )

    try:
        context = KnowledgeBaseService.build_context(venue)
        if availability_note:
            context = f'{context}\n\n{availability_note}'
        system_prompt = SALES_PERSONA_PROMPT.format(venue_name=venue.name, context=context)
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


@shared_task
def process_inbound_non_text_whatsapp_message(*, phone_number_id, from_wa_id, message_id, message_type):
    """Escalates to a human instead of replying: the AI can't act on non-text
    messages (image, audio, document, ...), so this records the message, marks
    the lead as needing human attention (if not already), and notifies staff."""
    try:
        venue = Venue.objects.get(whatsapp_phone_number_id=phone_number_id, is_active=True)
    except Venue.DoesNotExist:
        return

    conversation = ConversationService.get_or_create_conversation(
        venue=venue, external_contact_id=from_wa_id,
    )

    label = NON_TEXT_MESSAGE_LABELS.get(message_type, 'um arquivo')
    _, created = ConversationService.get_or_create_inbound_message(
        conversation=conversation,
        sender_type=Message.SenderType.CUSTOMER,
        content=f'[Cliente enviou {label} — tipo não suportado pela IA: {message_type}]',
        external_message_id=message_id,
    )
    if not created:
        # A redelivered webhook for a message we've already recorded.
        return

    lead = CRMService.get_or_create_lead(conversation=conversation, customer_phone=from_wa_id)
    CRMService.touch_interaction(lead)

    if lead.escalated_at:
        # Already in human attendance — no need to escalate or notify again,
        # but the message above is still recorded for the team to see.
        return

    lead.escalated_at = timezone.now()
    lead.save(update_fields=['escalated_at', 'updated_at'])
    CRMService.log_activity(
        lead=lead,
        activity_type=LeadActivity.ActivityType.ESCALATION,
        description=f'Escalonado automaticamente: cliente enviou {label}, que a IA não consegue processar.',
    )

    try:
        send_escalation_notification.delay(lead.id)
    except Exception:
        logger.exception('Failed to queue escalation notification for lead %s', lead.id)

    try:
        WhatsAppClient(phone_number_id).send_text(to=from_wa_id, body=NON_TEXT_ESCALATION_ACK)
        ConversationService.record_message(
            conversation=conversation,
            direction=Message.Direction.OUTBOUND,
            sender_type=Message.SenderType.AI,
            content=NON_TEXT_ESCALATION_ACK,
        )
    except Exception:
        logger.exception('Failed to send escalation ack to %s', from_wa_id)
