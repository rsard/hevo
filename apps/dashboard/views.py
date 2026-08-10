from collections import Counter
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.conversation.models import Message
from apps.crm.models import Lead, LeadActivity, Visit
from apps.user.services import get_active_venue

WEEKS_TO_SHOW = 8

PERIOD_CHOICES = {
    '7': ('7 dias', 7),
    '30': ('30 dias', 30),
    '90': ('90 dias', 90),
    'all': ('Todo o período', None),
}
DEFAULT_PERIOD = '30'

# Contacted and Qualified are parallel outcomes of the first qualification pass
# (branching on score), not sequential — they share a funnel tier.
FUNNEL_STAGE_ORDER = {
    Lead.Stage.NEW: 0,
    Lead.Stage.CONTACTED: 1,
    Lead.Stage.QUALIFIED: 1,
    # Legacy stage values, merged into Negotiation; kept here so historical
    # LeadActivity records recorded before the merge still funnel correctly.
    'visit_scheduled': 2,
    'proposal_sent': 2,
    Lead.Stage.NEGOTIATION: 2,
    Lead.Stage.WON: 3,
}
FUNNEL_TIERS = [
    ('Novo Lead', 0),
    ('Contatado / Qualificado', 1),
    ('Em Negociação', 2),
    ('Concluído', 3),
]
# Validated: node scripts/validate_palette.js "<these>" --ordinal --surface "#ffffff" --mode light
FUNNEL_COLORS = ['#8fb4bc', '#437f8c', '#164c58', '#0a2e37']

WEEKDAY_LABELS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
# Sequential ramp (brand hue), one step per activity-heatmap level 1-4; level 0
# (no messages) uses the neutral border color in CSS instead, not this ramp.
# Validated: node scripts/validate_palette.js
#   "#8fbcc2,#67a1ab,#3f7a84,#1a5868" --ordinal --surface "#ffffff" --mode light


def _week_start(a_date):
    """Return the Monday of the week containing a_date."""
    return a_date - timedelta(days=a_date.weekday())


def _weekly_series(datetimes, week_starts):
    """Bucket datetimes into weekly counts, with each week's % of the peak week."""
    counts = Counter()
    for value in datetimes:
        bucket = _week_start(timezone.localtime(value).date())
        counts[bucket] += 1

    peak = max(counts.values(), default=0)
    return [
        {
            'label': week.strftime('%d/%m'),
            'count': counts.get(week, 0),
            'pct': round(counts.get(week, 0) / peak * 100) if peak else 0,
        }
        for week in week_starts
    ]


def _conversion_funnel(leads):
    """Count leads reaching each funnel tier, based on their highest stage ever
    reached (from stage-change history), plus % of total and % of prior tier."""
    lead_ids = list(leads.values_list('id', flat=True))
    total_leads = len(lead_ids)

    # Every lead starts at New (order 0); walk their stage_change history for
    # the highest tier they ever reached, even if they were later marked Lost.
    max_order_reached = dict.fromkeys(lead_ids, 0)
    transitions = LeadActivity.objects.filter(
        lead_id__in=lead_ids,
        activity_type=LeadActivity.ActivityType.STAGE_CHANGE,
        to_stage__in=FUNNEL_STAGE_ORDER.keys(),
    ).values_list('lead_id', 'to_stage')
    for lead_id, to_stage in transitions:
        order = FUNNEL_STAGE_ORDER[to_stage]
        if order > max_order_reached.get(lead_id, 0):
            max_order_reached[lead_id] = order

    funnel = []
    previous_count = None
    for (label, min_order), color in zip(FUNNEL_TIERS, FUNNEL_COLORS):
        count = sum(1 for order in max_order_reached.values() if order >= min_order)
        funnel.append({
            'label': label,
            'count': count,
            'color': color,
            'pct_of_total': round(count / total_leads * 100) if total_leads else 0,
            'pct_of_previous': round(count / previous_count * 100) if previous_count else None,
        })
        previous_count = count
    return funnel


def _activity_heatmap(datetimes):
    """Buckets timestamps into a weekday x hour grid (Monday=0..Sunday=6), each
    cell leveled 0-4 relative to the busiest slot — for a GitHub-style heatmap
    of when leads message in."""
    counts = Counter()
    for value in datetimes:
        local = timezone.localtime(value)
        counts[(local.weekday(), local.hour)] += 1

    peak = max(counts.values(), default=0)

    def level(count):
        if not count:
            return 0
        pct = count / peak
        if pct <= 0.25:
            return 1
        if pct <= 0.5:
            return 2
        if pct <= 0.75:
            return 3
        return 4

    rows = []
    for weekday, label in enumerate(WEEKDAY_LABELS):
        cells = []
        for hour in range(24):
            count = counts.get((weekday, hour), 0)
            cells.append({'hour': hour, 'count': count, 'level': level(count)})
        rows.append({'label': label, 'cells': cells})
    return rows


@login_required
def dashboard_home(request):
    """Render the venue's lead/visit dashboard for the selected time period."""
    venue = get_active_venue(request.user)
    if venue is None:
        # Staff accounts (e.g. system admins) may legitimately have no venue of
        # their own -- send them to the area they actually manage instead of 404ing.
        if request.user.is_staff:
            return redirect('backoffice:dashboard')
        raise Http404('Nenhum espaço associado a este usuário.')

    period = request.GET.get('period', DEFAULT_PERIOD)
    if period not in PERIOD_CHOICES:
        period = DEFAULT_PERIOD
    _, period_days = PERIOD_CHOICES[period]

    all_leads = Lead.objects.filter(venue=venue)
    today = timezone.localdate()

    leads = all_leads
    if period_days is not None:
        leads = leads.filter(created_at__date__gte=today - timedelta(days=period_days))

    won_count = leads.filter(stage=Lead.Stage.WON).count()
    lost_count = leads.filter(stage=Lead.Stage.LOST).count()
    closed_count = won_count + lost_count
    conversion_rate = round((won_count / closed_count) * 100, 1) if closed_count else None

    avg_score = leads.exclude(qualification_score__isnull=True).aggregate(avg=Avg('qualification_score'))['avg']

    open_stages = [
        value for value, _ in Lead.Stage.choices if value not in (Lead.Stage.WON, Lead.Stage.LOST)
    ]
    counts_by_stage = dict(
        leads.filter(stage__in=open_stages).values_list('stage').annotate(count=Count('id')),
    )
    pipeline_rows = [
        (label, counts_by_stage.get(value, 0))
        for value, label in Lead.Stage.choices
        if value in open_stages
    ]

    if period_days is not None:
        weeks_to_show = max(1, -(-period_days // 7))  # ceil division
    else:
        weeks_to_show = WEEKS_TO_SHOW

    week_starts = [
        _week_start(today) - timedelta(weeks=i) for i in range(weeks_to_show - 1, -1, -1)
    ]
    range_start = week_starts[0]

    weekly_leads = _weekly_series(
        leads.filter(created_at__date__gte=range_start).values_list('created_at', flat=True),
        week_starts,
    )
    weekly_visits = _weekly_series(
        Visit.objects.filter(venue=venue, created_at__date__gte=range_start)
        .values_list('created_at', flat=True),
        week_starts,
    )

    inbound_messages = Message.objects.filter(
        conversation__venue=venue, direction=Message.Direction.INBOUND,
    )
    if period_days is not None:
        inbound_messages = inbound_messages.filter(
            created_at__date__gte=today - timedelta(days=period_days),
        )
    activity_heatmap = _activity_heatmap(inbound_messages.values_list('created_at', flat=True))

    context = {
        'venue': venue,
        'period': period,
        'period_choices': PERIOD_CHOICES,
        'total_leads': leads.count(),
        'new_today': all_leads.filter(created_at__date=today).count(),
        'upcoming_visits': Visit.objects.filter(
            venue=venue,
            status__in=[Visit.Status.SCHEDULED, Visit.Status.CONFIRMED],
            scheduled_at__gte=timezone.now(),
        ).count(),
        'escalated_count': all_leads.filter(escalated_at__isnull=False).count(),
        'conversion_rate': conversion_rate,
        'avg_score': round(avg_score, 1) if avg_score is not None else None,
        'pipeline_rows': pipeline_rows,
        'weekly_leads': weekly_leads,
        'weekly_visits': weekly_visits,
        'funnel_data': _conversion_funnel(leads),
        'activity_heatmap': activity_heatmap,
    }
    return render(request, 'dashboard/home.html', context)
