from django.utils import timezone

from apps.crm.models import Lead, LeadActivity


class CRMService:
    """Core lead lifecycle operations: creation, stage changes, activity logging."""

    @staticmethod
    def get_or_create_lead(*, conversation, customer_phone, customer_name=''):
        """Returns the lead for a conversation, creating one and logging it if new."""
        lead, created = Lead.objects.get_or_create(
            conversation=conversation,
            defaults={
                'venue': conversation.venue,
                'customer_phone': customer_phone,
                'customer_name': customer_name,
            },
        )
        if created:
            CRMService.log_activity(
                lead=lead,
                activity_type=LeadActivity.ActivityType.NOTE,
                description='Lead criado a partir de uma nova conversa.',
            )
        return lead

    @staticmethod
    def update_stage(*, lead, stage, actor=None):
        """Updates a lead's stage and logs the change, if the stage actually changed."""
        if lead.stage == stage:
            return lead
        previous_stage = lead.stage
        previous_stage_display = lead.get_stage_display()
        lead.stage = stage
        lead.save(update_fields=['stage', 'updated_at'])
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.STAGE_CHANGE,
            description=f'Status passou de {previous_stage_display} para {lead.get_stage_display()}.',
            created_by=actor,
            from_stage=previous_stage,
            to_stage=stage,
        )
        return lead

    @staticmethod
    def log_activity(*, lead, activity_type, description, created_by=None, from_stage='', to_stage=''):
        """Creates a LeadActivity record for the given lead."""
        return LeadActivity.objects.create(
            lead=lead,
            activity_type=activity_type,
            description=description,
            created_by=created_by,
            from_stage=from_stage,
            to_stage=to_stage,
        )

    @staticmethod
    def touch_interaction(lead):
        """Updates the lead's last_interaction_at timestamp to now."""
        lead.last_interaction_at = timezone.now()
        lead.save(update_fields=['last_interaction_at', 'updated_at'])
        return lead
