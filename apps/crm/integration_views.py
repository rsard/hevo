from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect, render

from apps.crm.calendar import build_authorization_url, exchange_code, generate_state
from apps.crm.models import CalendarConnection
from apps.user.services import get_active_venue


@login_required
def integration_settings(request):
    """Renders the venue's integrations settings page (Google Calendar, WhatsApp)."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404("Nenhum espaço associado a este usuário.")
    connection = getattr(venue, "calendar_connection", None)
    return render(request, "crm/integration_settings.html", {
        "venue": venue,
        "connection": connection,
        "facebook_app_id": settings.FACEBOOK_APP_ID,
        "whatsapp_embedded_signup_config_id": settings.WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID,
        "whatsapp_api_version": settings.WHATSAPP_API_VERSION,
    })


@login_required
def calendar_connect(request):
    """Starts the Google OAuth flow to connect the venue's calendar."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404("Nenhum espaço associado a este usuário.")
    state = generate_state()
    request.session["google_oauth_state"] = state
    return redirect(build_authorization_url(request, state))


@login_required
def calendar_callback(request):
    """Handles the Google OAuth redirect: validates state, exchanges the code, and
    saves the calendar connection."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404("Nenhum espaço associado a este usuário.")

    if request.GET.get("error"):
        messages.error(request, "Conexão com o Google Calendar cancelada ou negada.")
        return redirect("crm:integration-settings")

    expected_state = request.session.pop("google_oauth_state", None)
    state = request.GET.get("state")
    if not state or state != expected_state:
        return HttpResponseBadRequest("Estado inválido.")

    code = request.GET.get("code")
    if not code:
        return HttpResponseBadRequest("Código de autorização ausente.")

    tokens = exchange_code(request, code)
    CalendarConnection.objects.update_or_create(
        venue=venue,
        defaults={
            "provider": CalendarConnection.Provider.GOOGLE,
            "calendar_id": "primary",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_expires_at": tokens["expires_at"],
        },
    )
    messages.success(request, "Google Calendar conectado com sucesso.")
    return redirect("crm:integration-settings")


@login_required
def calendar_disconnect(request):
    """Removes the venue's calendar connection."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404("Nenhum espaço associado a este usuário.")
    if request.method == "POST":
        CalendarConnection.objects.filter(venue=venue).delete()
        messages.success(request, "Google Calendar desconectado.")
    return redirect("crm:integration-settings")
