from django.db import migrations

STAGE_LABELS_TO_VALUES = {
    'New Lead': 'new',
    'Contacted': 'contacted',
    'Qualified': 'qualified',
    'Visit Scheduled': 'visit_scheduled',
    'Proposal Sent': 'proposal_sent',
    'Negotiation': 'negotiation',
    'Won': 'won',
    'Lost': 'lost',
}

PREFIX = 'Stage changed from '


def backfill_stage_transitions(apps, schema_editor):
    LeadActivity = apps.get_model('crm', 'LeadActivity')
    stage_changes = LeadActivity.objects.filter(activity_type='stage_change', from_stage='', to_stage='')
    for activity in stage_changes:
        if not activity.description.startswith(PREFIX):
            continue
        remainder = activity.description[len(PREFIX):].rstrip('.')
        if ' to ' not in remainder:
            continue
        from_label, to_label = remainder.split(' to ', 1)
        from_value = STAGE_LABELS_TO_VALUES.get(from_label.strip())
        to_value = STAGE_LABELS_TO_VALUES.get(to_label.strip())
        if not from_value or not to_value:
            continue
        activity.from_stage = from_value
        activity.to_stage = to_value
        activity.save(update_fields=['from_stage', 'to_stage'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0003_leadactivity_from_stage_leadactivity_to_stage'),
    ]

    operations = [
        migrations.RunPython(backfill_stage_transitions, noop_reverse),
    ]
