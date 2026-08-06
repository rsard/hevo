from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect, render

from apps.crm.calendar import build_authorization_url, exchange_code, generate_state
from apps.crm.models import CalendarConnection
from apps.user.services import get_active_venue


@login_required
def calendar_settings(request):
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')
    connection = getattr(venue, 'calendar_connection', None)
    return render(request, 'crm/calendar_settings.html', {'venue': venue, 'connection': connection})


@login_required
def calendar_connect(request):
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')
    state = generate_state()
    request.session['google_oauth_state'] = state
    return redirect(build_authorization_url(request, state))


@login_required
def calendar_callback(request):
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    if request.GET.get('error'):
        messages.error(request, 'Conexão com o Google Calendar cancelada ou negada.')
        return redirect('crm:calendar-settings')

    expected_state = request.session.pop('google_oauth_state', None)
    state = request.GET.get('state')
    if not state or state != expected_state:
        return HttpResponseBadRequest('Estado inválido.')

    code = request.GET.get('code')
    if not code:
        return HttpResponseBadRequest('Código de autorização ausente.')

    tokens = exchange_code(request, code)
    CalendarConnection.objects.update_or_create(
        venue=venue,
        defaults={
            'provider': CalendarConnection.Provider.GOOGLE,
            'calendar_id': 'primary',
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'token_expires_at': tokens['expires_at'],
        },
    )
    messages.success(request, 'Google Calendar conectado com sucesso.')
    return redirect('crm:calendar-settings')


@login_required
def calendar_disconnect(request):
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')
    if request.method == 'POST':
        CalendarConnection.objects.filter(venue=venue).delete()
        messages.success(request, 'Google Calendar desconectado.')
    return redirect('crm:calendar-settings')
