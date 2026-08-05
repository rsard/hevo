from django.utils import timezone

from apps.crm.models import Lead, LeadActivity


class CRMService:
    @staticmethod
    def get_or_create_lead(*, conversation, customer_phone, customer_name=''):
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
                description='Lead created from new conversation.',
            )
        return lead

    @staticmethod
    def update_stage(*, lead, stage, actor=None):
        if lead.stage == stage:
            return lead
        previous_stage = lead.stage
        previous_stage_display = lead.get_stage_display()
        lead.stage = stage
        lead.save(update_fields=['stage', 'updated_at'])
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.STAGE_CHANGE,
            description=f'Stage changed from {previous_stage_display} to {lead.get_stage_display()}.',
            created_by=actor,
            from_stage=previous_stage,
            to_stage=stage,
        )
        return lead

    @staticmethod
    def log_activity(*, lead, activity_type, description, created_by=None, from_stage='', to_stage=''):
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
        lead.last_interaction_at = timezone.now()
        lead.save(update_fields=['last_interaction_at', 'updated_at'])
        return lead
