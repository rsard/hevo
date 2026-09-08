import logging
import re

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

MARKDOWN_LINK_RE = re.compile(r'\[([^\]]+)\]\((https?://[^\s)]+)\)')

SALES_PERSONA_PROMPT = (
    "You are the AI sales assistant for {venue_name}, a wedding/event venue in Brazil. "
    "Talk to the customer in warm, natural Portuguese, like the venue's best salesperson. "
    "Answer only using the knowledge base below.\n\n"
    "Mandatory rules:\n"
    "- Ask qualifying questions (event date, guest count, budget) naturally over the "
    "conversation.\n"
    "- Only bring up scheduling a visit when the customer shows real interest — never as "
    'a generic sign-off. Never close a reply with boilerplate like "let me know if you '
    'have more questions" or "want to schedule a visit?" — answer and stop.\n'
    "- Never say you'll check something and answer later. If the knowledge base has a "
    "FATO DE DISPONIBILIDADE, state it immediately. If you're missing info needed to "
    "answer (like the event date), ask for it directly in this same reply.\n"
    "- You can't send photos in this chat. If the customer asks to see photos and the "
    "knowledge base has a Photos link, share that link and invite them to take a look — "
    "never claim to be sending or attaching a photo yourself.\n"
    "- This is WhatsApp, not a webpage: it doesn't render Markdown links. Never write a "
    "link as [text](url) — paste the raw URL by itself (e.g. https://example.com), plain "
    "text, so it stays clickable.\n\n"
    "Knowledge base:\n{context}"
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


def _strip_markdown_links(text):
    """WhatsApp shows [text](url) literally instead of rendering it as a link —
    the prompt says not to write it that way, but the model does it often enough
    that collapsing it down to the raw URL here is worth doing regardless."""
    return MARKDOWN_LINK_RE.sub(lambda m: m.group(2), text)


VISIT_CTA_LOOKBACK = 3


def _recent_visit_cta(history, lookback=VISIT_CTA_LOOKBACK):
    """Whether the AI already invited the customer to schedule a visit in one of
    its last few replies. The prompt alone doesn't reliably stop the model
    repeating that invitation every single message, so this turns "don't do it
    if you already did" into a fact about the actual conversation instead of a
    rule the model has to remember unprompted."""
    recent_replies = [m['content'] for m in history if m['role'] == 'assistant'][-lookback:]
    return any('visita' in reply.lower() for reply in recent_replies)


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
        history = ConversationService.get_history(conversation)

        context = KnowledgeBaseService.build_context(venue)
        if availability_note:
            context = f'{context}\n\n{availability_note}'
        if _recent_visit_cta(history):
            context = (
                f'{context}\n\nNOTA: você já convidou o cliente para agendar uma visita '
                'recentemente nesta conversa. Não repita esse convite nesta resposta — só '
                'traga o assunto de novo se o cliente pedir explicitamente.'
            )
        system_prompt = SALES_PERSONA_PROMPT.format(venue_name=venue.name, context=context)

        provider = get_provider()
        # Lower than the 0.7 default: this prompt has several formatting/behavior
        # rules (FATO DE DISPONIBILIDADE, no boilerplate sign-off) that a more
        # "creative" temperature makes the model follow less reliably.
        response = provider.generate(system_prompt=system_prompt, messages=history, temperature=0.4)
        log_usage(venue=venue, response=response, conversation=conversation)
        reply_text = _strip_markdown_links(response.content)

        # Send before recording: if the send raises, no outbound row exists, so a
        # retry correctly starts over instead of the already_replied check above
        # mistaking "we saved a reply" for "we actually delivered one".
        WhatsAppClient(phone_number_id).send_text(to=from_wa_id, body=reply_text)
        ConversationService.record_message(
            conversation=conversation,
            direction=Message.Direction.OUTBOUND,
            sender_type=Message.SenderType.AI,
            content=reply_text,
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
