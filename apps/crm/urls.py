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
    lead_export,
    lead_table,
    lead_escalate,
    lead_name_update,
    lead_resolve_escalation,
    lead_schedule_visit,
    lead_stage_update,
    lead_toggle_label,
    lead_urgency_update,
)

app_name = 'crm'

urlpatterns = [
    path('leads/', lead_board, name='lead-list'),
    path('leads/tabela/', lead_table, name='lead-table'),
    path('leads/exportar/', lead_export, name='lead-export'),
    path('leads/<int:pk>/', lead_detail, name='lead-detail'),
    path('leads/<int:pk>/estagio/', lead_stage_update, name='lead-stage-update'),
    path('leads/<int:pk>/urgencia/', lead_urgency_update, name='lead-urgency-update'),
    path('leads/<int:pk>/nome/', lead_name_update, name='lead-name-update'),
    path('leads/<int:pk>/visitas/', lead_schedule_visit, name='lead-schedule-visit'),
    path('leads/<int:pk>/escalar/', lead_escalate, name='lead-escalate'),
    path('leads/<int:pk>/resolver-escalonamento/', lead_resolve_escalation, name='lead-resolve-escalation'),
    path('leads/<int:pk>/notas/', lead_add_note, name='lead-add-note'),
    path('leads/<int:pk>/labels/<int:label_id>/alternar/', lead_toggle_label, name='lead-toggle-label'),

    path('agenda/', agenda, name='agenda'),

    path('calendario/', calendar_settings, name='calendar-settings'),
    path('calendario/conectar/', calendar_connect, name='calendar-connect'),
    path('calendario/callback/', calendar_callback, name='calendar-callback'),
    path('calendario/desconectar/', calendar_disconnect, name='calendar-disconnect'),

    path('labels/', LabelListView.as_view(), name='label-list'),
    path('labels/novo/', LabelCreateView.as_view(), name='label-create'),
    path('labels/<int:pk>/editar/', LabelUpdateView.as_view(), name='label-update'),
    path('labels/<int:pk>/excluir/', LabelDeleteView.as_view(), name='label-delete'),
]
