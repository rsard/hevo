import requests
from django.conf import settings

GRAPH_API_BASE = "https://graph.facebook.com"


def get_waba_phone_number_id(waba_id):
    """Looks up the first phone number registered to a WABA.

    Used for Coexistence signups (existing WhatsApp Business App users): Meta's
    popup only returns a waba_id there, since the number already exists and
    isn't newly registered — so we look it up ourselves instead."""
    url = f"{GRAPH_API_BASE}/{settings.WHATSAPP_API_VERSION}/{waba_id}/phone_numbers"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    numbers = response.json().get("data", [])
    return numbers[0]["id"] if numbers else None


def get_phone_number_display(phone_number_id):
    """Best-effort: the human-readable number for a phone_number_id (e.g. "+55
    61 99240-3933"), shown in Integrations. Returns '' if the call fails —
    never blocks connecting."""
    url = f"{GRAPH_API_BASE}/{settings.WHATSAPP_API_VERSION}/{phone_number_id}"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    try:
        response = requests.get(
            url, headers=headers, params={"fields": "display_phone_number"}, timeout=10,
        )
        response.raise_for_status()
        return response.json().get("display_phone_number", "")
    except requests.RequestException:
        return ""


def extract_message_id(response):
    """Pulls the Meta-assigned wamid out of a send_* response, so callers can
    record it as external_message_id — that's what a later delivery-status
    webhook references, and it's the only way to match one back to a Message.
    Returns '' if the response doesn't have one."""
    messages = response.get("messages") or []
    return messages[0]["id"] if messages else ""


def create_message_template(waba_id, *, name, category, language, body_text, body_example=None):
    """Creates a message template on a WABA.

    Raises requests.HTTPError if Meta rejects it — including if a template with
    this name already exists on the WABA, which callers should treat as fine
    (nothing to do) rather than a real failure."""
    url = f"{GRAPH_API_BASE}/{settings.WHATSAPP_API_VERSION}/{waba_id}/message_templates"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    body_component = {"type": "BODY", "text": body_text}
    if body_example:
        body_component["example"] = {"body_text": [body_example]}
    payload = {
        "name": name,
        "language": language,
        "category": category,
        "components": [body_component],
    }
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def subscribe_app_to_waba(waba_id):
    """Subscribes our app to a WhatsApp Business Account's webhooks.

    Called once, right after a venue completes Embedded Signup: their WABA
    doesn't send us any events (messages, statuses) until our app is
    explicitly subscribed to it. Uses Hevo's own System User token — the one
    configured for sending messages — which Embedded Signup grants access to
    every WABA connected through our Tech Provider config, so no per-venue
    token is needed here."""
    url = f"{GRAPH_API_BASE}/{settings.WHATSAPP_API_VERSION}/{waba_id}/subscribed_apps"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    response = requests.post(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


class WhatsAppClient:
    """Thin client for sending outbound messages via the WhatsApp Cloud API."""

    def __init__(self, phone_number_id):
        """Sets up the API URL and auth headers for the given WhatsApp phone number."""
        self.phone_number_id = phone_number_id
        self._url = f"{GRAPH_API_BASE}/{settings.WHATSAPP_API_VERSION}/{phone_number_id}/messages"
        self._headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

    def send_text(self, *, to, body):
        """Sends a free-form text message to a WhatsApp contact."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        response = requests.post(self._url, headers=self._headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()

    def send_template(self, *, to, template_name, language_code, body_params=None):
        """Outside the 24h customer-service window, WhatsApp only allows
        pre-approved template messages, not free-form text."""
        template = {"name": template_name, "language": {"code": language_code}}
        if body_params:
            template["components"] = [
                {"type": "body", "parameters": [{"type": "text", "text": p} for p in body_params]},
            ]
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": template,
        }
        response = requests.post(self._url, headers=self._headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()

    def upload_media(self, *, file_bytes, filename, mime_type):
        """Uploads a file to WhatsApp's media storage, returning its media_id —
        the first step to sending a document/image/etc, which can't be attached
        to a message directly."""
        url = f"{GRAPH_API_BASE}/{settings.WHATSAPP_API_VERSION}/{self.phone_number_id}/media"
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
        files = {"file": (filename, file_bytes, mime_type)}
        data = {"messaging_product": "whatsapp", "type": mime_type}
        response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        response.raise_for_status()
        return response.json()["id"]

    def send_document(self, *, to, media_id, filename, caption=""):
        """Sends a previously uploaded file (see upload_media) as a document message."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {"id": media_id, "filename": filename, "caption": caption},
        }
        response = requests.post(self._url, headers=self._headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
