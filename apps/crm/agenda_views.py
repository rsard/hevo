import datetime as dt
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from google.auth.exceptions import RefreshError

from apps.crm.calendar import GoogleCalendarProvider
from apps.user.services import get_active_venue

WEEKS_TO_SHOW = 4

WEEKDAY_SHORT_PT = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
MONTH_NAMES_PT = [
    'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]


def _week_start(a_date):
    """Returns the Monday of the week containing the given date."""
    return a_date - timedelta(days=a_date.weekday())


def _week_label(week_start, week_end):
    """Formats a week's date range in Portuguese for display in the agenda header."""
    if week_start.month == week_end.month:
        return f'{week_start.day} - {week_end.day} de {MONTH_NAMES_PT[week_end.month - 1]}'
    return (
        f'{week_start.day} de {MONTH_NAMES_PT[week_start.month - 1]} - '
        f'{week_end.day} de {MONTH_NAMES_PT[week_end.month - 1]}'
    )


@login_required
def agenda(request):
    """Renders the venue's agenda: a 4-week grid of events from the connected calendar."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    try:
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        offset = 0

    connection = getattr(venue, 'calendar_connection', None)
    weeks = []
    error = None

    if connection:
        today = timezone.localdate()
        range_start = _week_start(today) + timedelta(weeks=offset * WEEKS_TO_SHOW)
        range_end = range_start + timedelta(weeks=WEEKS_TO_SHOW)

        try:
            time_min = timezone.make_aware(dt.datetime.combine(range_start, dt.time.min))
            time_max = timezone.make_aware(dt.datetime.combine(range_end, dt.time.min))
            events = GoogleCalendarProvider().list_events(
                connection=connection, time_min=time_min, time_max=time_max, max_results=250,
            )
        except RefreshError:
            # The stored refresh token no longer works (revoked access, or the
            # OAuth client's credentials were rotated after this connection was
            # made) — the venue needs to reconnect, not just retry.
            error = (
                'A conexão com o Google Calendar expirou ou foi revogada. '
                'Reconecte em Configurações → Integrações.'
            )
        except Exception:
            error = 'Não foi possível carregar os eventos do Google Calendar.'
        else:
            events_by_day = {}
            for event in events:
                events_by_day.setdefault(event['day'], []).append(event)

            for w in range(WEEKS_TO_SHOW):
                week_start = range_start + timedelta(weeks=w)
                week_end = week_start + timedelta(days=6)
                days = [
                    {
                        'number': (week_start + timedelta(days=d)).day,
                        'is_today': (week_start + timedelta(days=d)) == today,
                        'events': events_by_day.get(week_start + timedelta(days=d), []),
                    }
                    for d in range(7)
                ]
                weeks.append({'label': _week_label(week_start, week_end), 'days': days})

    return render(request, 'crm/agenda.html', {
        'venue': venue,
        'connection': connection,
        'weekday_names': WEEKDAY_SHORT_PT,
        'weeks': weeks,
        'error': error,
        'offset': offset,
        'prev_offset': offset - 1,
        'next_offset': offset + 1,
    })
