from datetime import timedelta
from itertools import groupby

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from apps.crm.calendar import GoogleCalendarProvider
from apps.user.services import get_active_venue

AGENDA_WINDOW = timedelta(days=30)

WEEKDAY_NAMES_PT = [
    'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira',
    'Sexta-feira', 'Sábado', 'Domingo',
]
MONTH_NAMES_PT = [
    'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]


def _day_header(day):
    today = timezone.localdate()
    if day == today:
        prefix = 'Hoje'
    elif day == today + timedelta(days=1):
        prefix = 'Amanhã'
    else:
        prefix = WEEKDAY_NAMES_PT[day.weekday()]
    return f'{prefix}, {day.day} de {MONTH_NAMES_PT[day.month - 1]}'


@login_required
def agenda(request):
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhuma venue associada a este usuário.')

    connection = getattr(venue, 'calendar_connection', None)
    events_by_day = []
    error = None

    if connection:
        try:
            now = timezone.now()
            events = GoogleCalendarProvider().list_events(
                connection=connection, time_min=now, time_max=now + AGENDA_WINDOW,
            )
        except Exception:
            error = 'Não foi possível carregar os eventos do Google Calendar.'
        else:
            events_by_day = [
                {'header': _day_header(day), 'events': list(day_events)}
                for day, day_events in groupby(events, key=lambda event: event['day'])
            ]

    return render(request, 'crm/agenda.html', {
        'venue': venue,
        'connection': connection,
        'events_by_day': events_by_day,
        'error': error,
    })
