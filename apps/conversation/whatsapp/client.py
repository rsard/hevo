import requests
from django.conf import settings

GRAPH_API_BASE = 'https://graph.facebook.com'


class WhatsAppClient:
    """Thin client for sending outbound messages via the WhatsApp Cloud API."""

    def __init__(self, phone_number_id):
        """Sets up the API URL and auth headers for the given WhatsApp phone number."""
        self.phone_number_id = phone_number_id
        self._url = f'{GRAPH_API_BASE}/{settings.WHATSAPP_API_VERSION}/{phone_number_id}/messages'
        self._headers = {
            'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
            'Content-Type': 'application/json',
        }

    def send_text(self, *, to, body):
        """Sends a free-form text message to a WhatsApp contact."""
        payload = {
            'messaging_product': 'whatsapp',
            'to': to,
            'type': 'text',
            'text': {'body': body},
        }
        response = requests.post(self._url, headers=self._headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()

    def send_template(self, *, to, template_name, language_code, body_params=None):
        """Outside the 24h customer-service window, WhatsApp only allows
        pre-approved template messages, not free-form text."""
        template = {'name': template_name, 'language': {'code': language_code}}
        if body_params:
            template['components'] = [
                {'type': 'body', 'parameters': [{'type': 'text', 'text': p} for p in body_params]},
            ]
        payload = {
            'messaging_product': 'whatsapp',
            'to': to,
            'type': 'template',
            'template': template,
        }
        response = requests.post(self._url, headers=self._headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
