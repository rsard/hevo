import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Max, Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.urls import reverse_lazy
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.conversation.models import Message
from apps.core.views import VenueScopedViewMixin
from apps.crm.forms import LabelForm
from apps.crm.models import Label, Lead, LeadActivity
from apps.crm.services import CRMService, LeadExportService, SchedulingService
from apps.crm.tasks import send_escalation_notification
from apps.user.services import get_active_venue

logger = logging.getLogger(__name__)

STALE_THRESHOLD = timedelta(hours=24)
RECENT_ACTIVITIES_COUNT = 5


def _recent_activities(lead):
    """Returns the lead's most recent activities, newest first."""
    return lead.activities.order_by('-created_at')[:RECENT_ACTIVITIES_COUNT]


SORT_FIELDS = {
    'interaction': 'last_interaction_at',
    'score': 'qualification_score',
}
DEFAULT_SORT = '-interaction'


def _filtered_leads(venue, request):
    """Returns the venue's leads filtered by search query, label, escalation, and
    urgency from the request, along with the active filter values for the template."""
    leads = Lead.objects.filter(venue=venue).select_related('event_type', 'assigned_to').prefetch_related('labels')

    query = request.GET.get('q', '').strip()
    if query:
        leads = leads.filter(Q(customer_name__icontains=query) | Q(customer_phone__icontains=query))

    active_label = request.GET.get('label', '').strip()
    if active_label:
        leads = leads.filter(labels__id=active_label)

    escalated = request.GET.get('escalated', '').strip()
    if escalated:
        leads = leads.filter(escalated_at__isnull=False)

    active_urgency = request.GET.get('urgency', '').strip()
    if active_urgency in dict(Lead.Urgency.choices):
        leads = leads.filter(urgency=active_urgency)
    else:
        active_urgency = ''

    sort = request.GET.get('sort', DEFAULT_SORT)
    sort_field = sort.lstrip('-')
    if sort_field not in SORT_FIELDS:
        sort = DEFAULT_SORT
        sort_field = sort.lstrip('-')
    direction = '-' if sort.startswith('-') else ''
    leads = leads.order_by(f'{direction}{SORT_FIELDS[sort_field]}')

    return leads, query, active_label, escalated, active_urgency, sort


@login_required
@ensure_csrf_cookie
def lead_board(request):
    """Renders the kanban board of leads grouped by stage, with search/label filters."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    leads, query, active_label, escalated, active_urgency, sort = _filtered_leads(venue, request)
    leads = list(leads)
    _annotate_staleness(leads)

    leads_by_stage = {}
    for lead in leads:
        leads_by_stage.setdefault(lead.stage, []).append(lead)

    columns = [
        {'value': value, 'label': label, 'leads': leads_by_stage.get(value, [])}
        for value, label in Lead.Stage.choices
    ]

    context = {
        'venue': venue,
        'columns': columns,
        'query': query,
        'all_labels': Label.objects.filter(venue=venue),
        'active_label': active_label,
        'escalated': escalated,
        'active_urgency': active_urgency,
        'urgencies': Lead.Urgency.choices,
    }
    template = 'crm/_kanban_container.html' if request.htmx else 'crm/lead_board.html'
    return render(request, template, context)


@login_required
def lead_table(request):
    """Renders the leads as a flat, filterable table."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    leads, query, active_label, escalated, active_urgency, sort = _filtered_leads(venue, request)
    leads = list(leads)
    _annotate_staleness(leads)

    context = {
        'venue': venue,
        'leads': leads,
        'query': query,
        'all_labels': Label.objects.filter(venue=venue),
        'active_label': active_label,
        'escalated': escalated,
        'active_urgency': active_urgency,
        'urgencies': Lead.Urgency.choices,
        'sort': sort,
    }
    return render(request, 'crm/lead_table.html', context)


@login_required
def lead_export(request):
    """Downloads the currently filtered leads as an .xlsx spreadsheet."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    leads, *_ = _filtered_leads(venue, request)
    content = LeadExportService.to_xlsx(leads)

    filename = f'leads-{venue.slug}-{timezone.localdate().isoformat()}.xlsx'
    response = HttpResponse(
        content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _annotate_staleness(leads):
    """Flags each lead as stale if its last inbound message is 24h+ old and it's
    still in an open (non-Won/Lost) stage."""
    if not leads:
        return
    last_inbound_by_conversation = dict(
        Message.objects.filter(conversation__lead__in=leads, direction=Message.Direction.INBOUND)
        .values('conversation_id')
        .annotate(last=Max('created_at'))
        .values_list('conversation_id', 'last'),
    )
    now = timezone.now()
    for lead in leads:
        last_inbound = last_inbound_by_conversation.get(lead.conversation_id)
        lead.is_stale = bool(
            last_inbound
            and (now - last_inbound) > STALE_THRESHOLD
            and lead.stage not in (Lead.Stage.WON, Lead.Stage.LOST)
        )


@login_required
@ensure_csrf_cookie
def lead_detail(request, pk):
    """Renders the detail page for a single lead: conversation, activities, labels."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    lead = get_object_or_404(
        Lead.objects.filter(venue=venue)
        .select_related('event_type', 'assigned_to', 'conversation')
        .prefetch_related('labels'),
        pk=pk,
    )
    assigned_labels = list(lead.labels.all())
    assigned_label_ids = {label.id for label in assigned_labels}
    context = {
        'lead': lead,
        'stages': Lead.Stage.choices,
        'urgencies': Lead.Urgency.choices,
        'conversation_messages': lead.conversation.messages.all(),
        'activities': _recent_activities(lead),
        'unassigned_labels': Label.objects.filter(venue=venue).exclude(id__in=assigned_label_ids),
    }
    return render(request, 'crm/lead_detail.html', context)


@login_required
@require_POST
def lead_stage_update(request, pk):
    """Updates a lead's funnel stage from a POSTed value."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    lead = get_object_or_404(Lead.objects.filter(venue=venue), pk=pk)
    stage = request.POST.get('stage')
    if stage not in dict(Lead.Stage.choices):
        return HttpResponseBadRequest('Estágio inválido.')

    CRMService.update_stage(lead=lead, stage=stage, actor=request.user)

    if request.POST.get('render') == 'field':
        return render(request, 'crm/_lead_stage_field.html', {'lead': lead, 'stages': Lead.Stage.choices})
    return render(request, 'crm/_lead_card.html', {'lead': lead})


@login_required
@require_POST
def lead_urgency_update(request, pk):
    """Updates a lead's urgency level from a POSTed value."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    lead = get_object_or_404(Lead.objects.filter(venue=venue), pk=pk)
    urgency = request.POST.get('urgency')
    if urgency not in dict(Lead.Urgency.choices):
        return HttpResponseBadRequest('Urgência inválida.')

    lead.urgency = urgency
    lead.save(update_fields=['urgency', 'updated_at'])

    return render(request, 'crm/_lead_urgency_field.html', {'lead': lead, 'urgencies': Lead.Urgency.choices})


@login_required
@require_POST
def lead_name_update(request, pk):
    """Updates a lead's customer name from a POSTed value."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    lead = get_object_or_404(Lead.objects.filter(venue=venue), pk=pk)
    lead.customer_name = request.POST.get('customer_name', '').strip()
    lead.save(update_fields=['customer_name', 'updated_at'])

    return render(request, 'crm/_lead_name_field.html', {'lead': lead})


@login_required
@require_POST
def lead_schedule_visit(request, pk):
    """Schedules a visit for the lead at the POSTed date/time, if the slot is available."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    lead = get_object_or_404(Lead.objects.filter(venue=venue), pk=pk)

    parsed = parse_datetime(request.POST.get('scheduled_at', ''))
    visit_error = None
    visit_success = False
    if parsed is None:
        visit_error = 'Informe uma data e hora válidas.'
    else:
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed)
        try:
            SchedulingService.schedule_visit(lead=lead, start=parsed)
            visit_success = True
        except ValueError:
            visit_error = 'Horário indisponível para este espaço. Escolha outro.'

    lead.refresh_from_db()
    return render(request, 'crm/_visits_section.html', {
        'lead': lead, 'visit_error': visit_error, 'visit_success': visit_success,
    })


@login_required
@require_POST
def lead_escalate(request, pk):
    """Manually marks a lead as escalated and queues a staff notification."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    lead = get_object_or_404(Lead.objects.filter(venue=venue), pk=pk)
    if lead.escalated_at is None:
        lead.escalated_at = timezone.now()
        lead.save(update_fields=['escalated_at', 'updated_at'])
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.ESCALATION,
            description=f'Escalonado manualmente por {request.user.get_username()}.',
            created_by=request.user,
        )
        try:
            send_escalation_notification.delay(lead.id)
        except Exception:
            # The escalation itself already saved — a broker hiccup here
            # shouldn't 500 the request and leave the UI looking stale.
            logger.exception('Failed to queue escalation notification for lead %s', lead.id)
    return render(request, 'crm/_escalation_banner.html', {'lead': lead})


@login_required
@require_POST
def lead_resolve_escalation(request, pk):
    """Clears a lead's escalation flag and logs the resolution."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    lead = get_object_or_404(Lead.objects.filter(venue=venue), pk=pk)
    if lead.escalated_at:
        lead.escalated_at = None
        lead.save(update_fields=['escalated_at', 'updated_at'])
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.HUMAN_ACTION,
            description=f'Escalonamento resolvido por {request.user.get_username()}.',
            created_by=request.user,
        )
    return render(request, 'crm/_escalation_banner.html', {'lead': lead})


@login_required
@require_POST
def lead_add_note(request, pk):
    """Adds a manual note to the lead's activity log."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    lead = get_object_or_404(Lead.objects.filter(venue=venue), pk=pk)
    content = request.POST.get('content', '').strip()
    note_success = False
    if content:
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.NOTE,
            description=content,
            created_by=request.user,
        )
        note_success = True
    return render(request, 'crm/_activity_list.html', {
        'activities': _recent_activities(lead), 'note_success': note_success,
    })


@login_required
@require_POST
def lead_toggle_label(request, pk, label_id):
    """Adds or removes a label from a lead, toggling its current assignment."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    lead = get_object_or_404(Lead.objects.filter(venue=venue).prefetch_related('labels'), pk=pk)
    label = get_object_or_404(Label.objects.filter(venue=venue), pk=label_id)
    if lead.labels.filter(pk=label.pk).exists():
        lead.labels.remove(label)
    else:
        lead.labels.add(label)
    assigned_label_ids = {label.id for label in lead.labels.all()}
    return render(request, 'crm/_label_picker.html', {
        'lead': lead,
        'unassigned_labels': Label.objects.filter(venue=venue).exclude(id__in=assigned_label_ids),
    })


class LabelListView(VenueScopedViewMixin, ListView):
    model = Label
    template_name = 'crm/label_list.html'
    context_object_name = 'items'


class LabelCreateView(VenueScopedViewMixin, CreateView):
    model = Label
    form_class = LabelForm
    template_name = 'crm/label_form.html'
    success_url = reverse_lazy('crm:label-list')


class LabelUpdateView(VenueScopedViewMixin, UpdateView):
    model = Label
    form_class = LabelForm
    template_name = 'crm/label_form.html'
    success_url = reverse_lazy('crm:label-list')


class LabelDeleteView(VenueScopedViewMixin, DeleteView):
    model = Label
    template_name = 'venue/confirm_delete.html'
    success_url = reverse_lazy('crm:label-list')
    extra_context = {'section_title': 'Configurações', 'nav_template': 'venue/_account_nav.html'}
