from django.urls import path

from apps.crm.agenda_views import agenda
from apps.crm.integration_views import (
    calendar_callback,
    calendar_connect,
    calendar_disconnect,
    calendar_settings,
)
from apps.crm.views import (
    LabelCreateView,
    LabelDeleteView,
    LabelListView,
    LabelUpdateView,
    lead_add_note,
    lead_board,
    lead_detail,
    lead_resolve_escalation,
    lead_schedule_visit,
    lead_stage_update,
    lead_toggle_label,
)

app_name = 'crm'

urlpatterns = [
    path('leads/', lead_board, name='lead-list'),
    path('leads/<int:pk>/', lead_detail, name='lead-detail'),
    path('leads/<int:pk>/stage/', lead_stage_update, name='lead-stage-update'),
    path('leads/<int:pk>/visits/', lead_schedule_visit, name='lead-schedule-visit'),
    path('leads/<int:pk>/resolve-escalation/', lead_resolve_escalation, name='lead-resolve-escalation'),
    path('leads/<int:pk>/notes/', lead_add_note, name='lead-add-note'),
    path('leads/<int:pk>/labels/<int:label_id>/toggle/', lead_toggle_label, name='lead-toggle-label'),

    path('agenda/', agenda, name='agenda'),

    path('calendar/', calendar_settings, name='calendar-settings'),
    path('calendar/connect/', calendar_connect, name='calendar-connect'),
    path('calendar/callback/', calendar_callback, name='calendar-callback'),
    path('calendar/disconnect/', calendar_disconnect, name='calendar-disconnect'),

    path('labels/', LabelListView.as_view(), name='label-list'),
    path('labels/new/', LabelCreateView.as_view(), name='label-create'),
    path('labels/<int:pk>/edit/', LabelUpdateView.as_view(), name='label-update'),
    path('labels/<int:pk>/delete/', LabelDeleteView.as_view(), name='label-delete'),
]
