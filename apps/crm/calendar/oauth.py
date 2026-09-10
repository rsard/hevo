import secrets
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
# email is non-sensitive (no extra verification burden) — just lets Integrations
# show which Google account is connected, not used for login/identity.
SCOPE = "https://www.googleapis.com/auth/calendar.events email"


def generate_state():
    """Generates a random state token to protect the OAuth flow against CSRF."""
    return secrets.token_urlsafe(32)


def _redirect_uri(request):
    """Builds the absolute callback URL Google should redirect to after auth."""
    return request.build_absolute_uri(reverse("crm:calendar-callback"))


def build_authorization_url(request, state):
    """Builds the Google OAuth consent screen URL for connecting a calendar."""
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": _redirect_uri(request),
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTHORIZATION_URL}?{urlencode(params)}"


def exchange_code(request, code):
    """Exchanges an OAuth authorization code for access/refresh tokens and expiry."""
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": _redirect_uri(request),
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": timezone.now() + timedelta(seconds=data["expires_in"]),
    }


def fetch_account_email(access_token):
    """Best-effort: which Google account this connection is for, shown in
    Integrations. Returns '' if the call fails — never blocks connecting."""
    try:
        response = requests.get(
            USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=10,
        )
        response.raise_for_status()
        return response.json().get("email", "")
    except requests.RequestException:
        return ""
