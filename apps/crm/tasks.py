from celery import shared_task

from apps.crm.models import LeadActivity
from apps.crm.services import CRMService, FollowUpService
from apps.venue.models import Venue


@shared_task
def send_followups_for_all_venues():
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
def mark_inactive_leads_as_lost():
    for venue in Venue.objects.filter(is_active=True):
        FollowUpService.mark_inactive_leads_as_lost(venue)
