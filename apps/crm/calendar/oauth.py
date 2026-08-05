import secrets
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
SCOPE = 'https://www.googleapis.com/auth/calendar'


def generate_state():
    return secrets.token_urlsafe(32)


def _redirect_uri(request):
    return request.build_absolute_uri(reverse('crm:calendar-callback'))


def build_authorization_url(request, state):
    params = {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': _redirect_uri(request),
        'response_type': 'code',
        'scope': SCOPE,
        'access_type': 'offline',
        'prompt': 'consent',
        'state': state,
    }
    return f'{AUTHORIZATION_URL}?{urlencode(params)}'


def exchange_code(request, code):
    response = requests.post(
        TOKEN_URL,
        data={
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': _redirect_uri(request),
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return {
        'access_token': data['access_token'],
        'refresh_token': data['refresh_token'],
        'expires_at': timezone.now() + timedelta(seconds=data['expires_in']),
    }
