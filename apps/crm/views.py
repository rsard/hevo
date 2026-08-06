from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Max, Q
from django.http import Http404, HttpResponseBadRequest
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
from apps.crm.services import CRMService, SchedulingService
from apps.user.services import get_active_venue

STALE_THRESHOLD = timedelta(hours=24)


@login_required
@ensure_csrf_cookie
def lead_board(request):
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    leads = Lead.objects.filter(venue=venue).select_related('event_type', 'assigned_to').prefetch_related('labels')
    leads = leads.order_by('-last_interaction_at')

    query = request.GET.get('q', '').strip()
    if query:
        leads = leads.filter(Q(customer_name__icontains=query) | Q(customer_phone__icontains=query))

    active_label = request.GET.get('label', '').strip()
    if active_label:
        leads = leads.filter(labels__id=active_label)

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
    }
    template = 'crm/_kanban_board.html' if request.htmx else 'crm/lead_board.html'
    return render(request, template, context)


def _annotate_staleness(leads):
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
        'conversation_messages': lead.conversation.messages.all(),
        'activities': lead.activities.all(),
        'unassigned_labels': Label.objects.filter(venue=venue).exclude(id__in=assigned_label_ids),
    }
    return render(request, 'crm/lead_detail.html', context)


@login_required
@require_POST
def lead_stage_update(request, pk):
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
def lead_schedule_visit(request, pk):
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    lead = get_object_or_404(Lead.objects.filter(venue=venue), pk=pk)

    parsed = parse_datetime(request.POST.get('scheduled_at', ''))
    visit_error = None
    if parsed is None:
        visit_error = 'Informe uma data e hora válidas.'
    else:
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed)
        try:
            SchedulingService.schedule_visit(lead=lead, start=parsed)
        except ValueError:
            visit_error = 'Horário indisponível para este espaço. Escolha outro.'

    lead.refresh_from_db()
    return render(request, 'crm/_visits_section.html', {'lead': lead, 'visit_error': visit_error})


@login_required
@require_POST
def lead_resolve_escalation(request, pk):
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
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    lead = get_object_or_404(Lead.objects.filter(venue=venue), pk=pk)
    content = request.POST.get('content', '').strip()
    if content:
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.NOTE,
            description=content,
            created_by=request.user,
        )
    return render(request, 'crm/_activity_list.html', {'activities': lead.activities.all()})


@login_required
@require_POST
def lead_toggle_label(request, pk, label_id):
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
