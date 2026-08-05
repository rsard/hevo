import requests
from django.conf import settings

GRAPH_API_BASE = 'https://graph.facebook.com'


class WhatsAppClient:
    def __init__(self, phone_number_id):
        self.phone_number_id = phone_number_id
        self._url = f'{GRAPH_API_BASE}/{settings.WHATSAPP_API_VERSION}/{phone_number_id}/messages'
        self._headers = {
            'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
            'Content-Type': 'application/json',
        }

    def send_text(self, *, to, body):
        payload = {
            'messaging_product': 'whatsapp',
            'to': to,
            'type': 'text',
            'text': {'body': body},
        }
        response = requests.post(self._url, headers=self._headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
