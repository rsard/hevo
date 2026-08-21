import logging

from celery import shared_task

from apps.crm.models import Lead, LeadActivity
from apps.crm.services import CRMService, FollowUpService, NotificationService, ReminderService
from apps.venue.models import Venue

logger = logging.getLogger(__name__)


@shared_task
def send_followups_for_all_venues():
    """Celery task: sends follow-up messages to stale leads across all active venues."""
    for venue in Venue.objects.filter(is_active=True):
        for lead in FollowUpService.leads_needing_followup(venue):
            try:
                FollowUpService.send_followup(lead)
            except Exception as exc:
                logger.exception('Failed to send automated follow-up for lead %s', lead.pk)
                CRMService.log_activity(
                    lead=lead,
                    activity_type=LeadActivity.ActivityType.ERROR,
                    description=f'Falha ao enviar follow-up automático: {exc}',
                )


@shared_task
def send_escalation_notification(lead_id):
    """Celery task: notifies venue staff that a lead requested human attention."""
    lead = Lead.objects.select_related('venue').get(pk=lead_id)
    try:
        NotificationService.notify_escalation(lead)
    except Exception as exc:
        logger.exception('Failed to send escalation notification for lead %s', lead.pk)
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.ERROR,
            description=f'Falha ao enviar notificação de escalonamento: {exc}',
        )


@shared_task
def send_visit_reminders_for_all_venues():
    """Celery task: sends a WhatsApp reminder for each upcoming, unreminded
    visit, across all active venues."""
    for venue in Venue.objects.filter(is_active=True):
        for visit in ReminderService.visits_needing_reminder(venue):
            try:
                ReminderService.send_reminder(visit)
            except Exception as exc:
                logger.exception('Failed to send automated visit reminder for visit %s', visit.pk)
                CRMService.log_activity(
                    lead=visit.lead,
                    activity_type=LeadActivity.ActivityType.ERROR,
                    description=f'Falha ao enviar lembrete de visita automático: {exc}',
                )


@shared_task
def mark_inactive_leads_as_lost():
    """Celery task: marks long-silent leads as lost across all active venues."""
    for venue in Venue.objects.filter(is_active=True):
        FollowUpService.mark_inactive_leads_as_lost(venue)
