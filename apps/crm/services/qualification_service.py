import json
from datetime import date

from django.utils import timezone

from apps.ai.services import get_provider, log_usage
from apps.conversation.models import Conversation, Message
from apps.conversation.services import ConversationService
from apps.conversation.whatsapp.client import WhatsAppClient
from apps.crm.models import Lead, LeadActivity
from apps.crm.services.crm_service import CRMService
from apps.crm.services.scheduling_service import SchedulingService
from apps.venue.models import EventType

SYSTEM_PROMPT = (
    'You are a sales qualification assistant for a wedding/event venue in Brazil. '
    'Given a WhatsApp conversation transcript with a customer, extract structured '
    'information about the lead and reply with ONLY a valid JSON object (no prose, '
    'no markdown fences) with these keys: event_type (string or null), '
    'event_date ("YYYY-MM-DD" or null), guest_count (integer or null), '
    'estimated_budget (number or null), qualification_score (integer 0-100), '
    'sentiment ("positive", "neutral" or "negative"), is_negotiating (true if the '
    'customer is discussing price, asking for discounts or different payment terms, '
    'or comparing with other venues; false otherwise), wants_human (true if the '
    'customer explicitly asks to talk to a person, a human, an attendant, or '
    'expresses frustration with the automated assistant; false otherwise), '
    'summary (one paragraph, in Portuguese, summarizing what the customer wants).'
)

QUALIFIED_SCORE_THRESHOLD = 50

NEGOTIATION_ELIGIBLE_STAGES = {
    Lead.Stage.CONTACTED,
    Lead.Stage.QUALIFIED,
}


class QualificationService:
    """Uses AI to extract lead qualification data from the conversation transcript."""

    @staticmethod
    def qualify(lead):
        """Runs the AI qualification prompt on the conversation and applies the result."""
        conversation = lead.conversation
        history = ConversationService.get_history(conversation, limit=50)
        if not history:
            return lead

        provider = get_provider()
        response = provider.generate(system_prompt=SYSTEM_PROMPT, messages=history, temperature=0.2)
        log_usage(venue=lead.venue, response=response, conversation=conversation)

        try:
            data = json.loads(response.content)
        except (json.JSONDecodeError, TypeError):
            CRMService.log_activity(
                lead=lead,
                activity_type=LeadActivity.ActivityType.AI_ACTION,
                description='Qualification failed: AI did not return valid JSON.',
            )
            return lead

        QualificationService._apply(lead, data)
        return lead

    @staticmethod
    def _apply(lead, data):
        """Updates lead fields from AI output and advances stage/escalation as needed."""
        event_type_name = data.get('event_type')
        if event_type_name:
            lead.event_type = EventType.objects.filter(
                venue=lead.venue, name__iexact=event_type_name,
            ).first()
        previous_event_date = lead.event_date
        if data.get('event_date'):
            try:
                lead.event_date = date.fromisoformat(data['event_date'])
            except ValueError:
                pass
        if data.get('guest_count') is not None:
            lead.guest_count = data['guest_count']
        if data.get('estimated_budget') is not None:
            lead.estimated_budget = data['estimated_budget']
        if data.get('qualification_score') is not None:
            lead.qualification_score = data['qualification_score']
        if data.get('sentiment'):
            lead.sentiment = data['sentiment']
        if data.get('summary'):
            lead.conversation_summary = data['summary']
        lead.save()

        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.AI_ACTION,
            description='AI updated qualification data from the conversation.',
        )

        if data.get('wants_human') and lead.escalated_at is None:
            lead.escalated_at = timezone.now()
            lead.save(update_fields=['escalated_at', 'updated_at'])
            CRMService.log_activity(
                lead=lead,
                activity_type=LeadActivity.ActivityType.ESCALATION,
                description='Cliente solicitou falar com uma pessoa da equipe.',
            )
            try:
                # Local import: apps.crm.tasks imports apps.crm.services, which
                # would otherwise be a circular import at module load time.
                from apps.crm.tasks import send_escalation_notification
                send_escalation_notification.delay(lead.id)
            except Exception:
                CRMService.log_activity(
                    lead=lead,
                    activity_type=LeadActivity.ActivityType.AI_ACTION,
                    description='Falha ao enfileirar notificação de escalonamento.',
                )

        if lead.stage == Lead.Stage.NEW:
            score = data.get('qualification_score') or 0
            next_stage = Lead.Stage.QUALIFIED if score >= QUALIFIED_SCORE_THRESHOLD else Lead.Stage.CONTACTED
            CRMService.update_stage(lead=lead, stage=next_stage)
        elif data.get('is_negotiating') and lead.stage in NEGOTIATION_ELIGIBLE_STAGES:
            CRMService.update_stage(lead=lead, stage=Lead.Stage.NEGOTIATION)
            CRMService.log_activity(
                lead=lead,
                activity_type=LeadActivity.ActivityType.AI_ACTION,
                description='IA detectou sinais de negociação na conversa.',
            )

        if lead.event_date and lead.event_date != previous_event_date:
            QualificationService._notify_if_date_unavailable(lead)

    @staticmethod
    def _notify_if_date_unavailable(lead):
        """If the AI just picked up a new (or changed) event date and the venue
        is already booked for it, proactively suggests the nearest open dates
        instead of letting the customer find out the hard way later."""
        if SchedulingService.is_event_date_available(
            venue=lead.venue, date=lead.event_date, exclude_lead=lead,
        ):
            return

        alternatives = SchedulingService.suggest_alternative_event_dates(
            venue=lead.venue, after=lead.event_date, exclude_lead=lead,
        )
        if not alternatives:
            return

        dates_text = ', '.join(d.strftime('%d/%m') for d in alternatives)
        content = (
            f'Notei que o dia {lead.event_date.strftime("%d/%m")} já está reservado '
            f'para outro evento em nosso espaço. Mas ainda temos essas datas '
            f'disponíveis por perto: {dates_text}. Alguma delas funcionaria pra você?'
        )

        conversation = lead.conversation
        if conversation.channel == Conversation.Channel.WHATSAPP:
            WhatsAppClient(lead.venue.whatsapp_phone_number_id).send_text(
                to=conversation.external_contact_id, body=content,
            )
        ConversationService.record_message(
            conversation=conversation,
            direction=Message.Direction.OUTBOUND,
            sender_type=Message.SenderType.AI,
            content=content,
        )
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.AI_ACTION,
            description=(
                f'Data {lead.event_date.strftime("%d/%m/%Y")} indisponível — '
                'sugeri datas alternativas automaticamente.'
            ),
        )
