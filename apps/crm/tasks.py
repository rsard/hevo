from celery import shared_task

from apps.crm.models import Lead, LeadActivity
from apps.crm.services import CRMService, FollowUpService, NotificationService, ReminderService
from apps.venue.models import Venue


@shared_task
def send_followups_for_all_venues():
    """Celery task: sends follow-up messages to stale leads across all active venues."""
    for venue in Venue.objects.filter(is_active=True):
        for lead in FollowUpService.leads_needing_followup(venue):
            try:
                FollowUpService.send_followup(lead)
            except Exception:
                CRMService.log_activity(
                    lead=lead,
                    activity_type=LeadActivity.ActivityType.AI_ACTION,
                    description='Falha ao enviar follow-up automático.',
                )


@shared_task
def send_escalation_notification(lead_id):
    """Celery task: notifies venue staff that a lead requested human attention."""
    lead = Lead.objects.select_related('venue').get(pk=lead_id)
    try:
        NotificationService.notify_escalation(lead)
    except Exception:
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.AI_ACTION,
            description='Falha ao enviar notificação de escalonamento.',
        )


@shared_task
def send_visit_reminders_for_all_venues():
    """Celery task: sends a WhatsApp reminder for each upcoming, unreminded
    visit, across all active venues."""
    for venue in Venue.objects.filter(is_active=True):
        for visit in ReminderService.visits_needing_reminder(venue):
            try:
                ReminderService.send_reminder(visit)
            except Exception:
                CRMService.log_activity(
                    lead=visit.lead,
                    activity_type=LeadActivity.ActivityType.AI_ACTION,
                    description='Falha ao enviar lembrete de visita automático.',
                )


@shared_task
def mark_inactive_leads_as_lost():
    """Celery task: marks long-silent leads as lost across all active venues."""
    for venue in Venue.objects.filter(is_active=True):
        FollowUpService.mark_inactive_leads_as_lost(venue)
