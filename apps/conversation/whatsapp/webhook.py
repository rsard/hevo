import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.conversation.tasks import (
    process_inbound_non_text_whatsapp_message,
    process_inbound_whatsapp_message,
    process_whatsapp_status_update,
)
from apps.conversation.whatsapp.parser import (
    extract_messages,
    extract_non_text_messages,
    extract_statuses,
)

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """WhatsApp Cloud API webhook: verification handshake on GET, messages on POST."""
    if request.method == "GET":
        return _handle_verification(request)
    return _handle_incoming(request)


def _handle_verification(request):
    """Responds to Meta's webhook verification handshake with the challenge if valid."""
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge", "")
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        return HttpResponse(challenge)
    return HttpResponseForbidden()


def _handle_incoming(request):
    """Verifies the signature, then queues each inbound message for async processing.
    Text messages get an AI reply; anything else (image, audio, ...) is escalated
    to a human instead, since the AI can't act on it."""
    if not _valid_signature(request):
        return HttpResponseForbidden()

    payload = json.loads(request.body)
    for phone_number_id, from_wa_id, message_id, text, contact_name in extract_messages(payload):
        try:
            process_inbound_whatsapp_message.delay(
                phone_number_id=phone_number_id,
                from_wa_id=from_wa_id,
                message_id=message_id,
                text=text,
                contact_name=contact_name,
            )
        except Exception:
            # A broker hiccup here shouldn't 500 the webhook — Meta retries
            # failed deliveries, but repeated 5xx responses risk it disabling
            # the subscription, and would also abandon the rest of this batch.
            logger.exception("Failed to queue inbound WhatsApp message %s", message_id)

    for phone_number_id, from_wa_id, message_id, message_type in extract_non_text_messages(payload):
        try:
            process_inbound_non_text_whatsapp_message.delay(
                phone_number_id=phone_number_id,
                from_wa_id=from_wa_id,
                message_id=message_id,
                message_type=message_type,
            )
        except Exception:
            logger.exception("Failed to queue inbound non-text WhatsApp message %s", message_id)

    for wamid, status, error_detail in extract_statuses(payload):
        try:
            process_whatsapp_status_update.delay(
                wamid=wamid, status=status, error_detail=error_detail,
            )
        except Exception:
            logger.exception("Failed to queue WhatsApp status update %s", wamid)

    return JsonResponse({"status": "received"})


def _valid_signature(request):
    """Verifies the payload's HMAC-SHA256 signature against the configured app secret."""
    if not settings.WHATSAPP_APP_SECRET:
        return False
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.WHATSAPP_APP_SECRET.encode(), request.body, hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature.removeprefix("sha256="), expected)
