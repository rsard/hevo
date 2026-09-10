def extract_messages(payload):
    """Yields (phone_number_id, from_wa_id, message_id, text, contact_name) for each
    inbound text message in a WhatsApp Cloud API webhook payload. contact_name is the
    sender's WhatsApp display name (empty string if Meta didn't include one). Non-text
    messages (image, audio, etc.) are handled separately by extract_non_text_messages."""
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            names_by_wa_id = {
                contact["wa_id"]: contact.get("profile", {}).get("name", "")
                for contact in value.get("contacts", [])
            }
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                yield (
                    phone_number_id,
                    message["from"],
                    message["id"],
                    message["text"]["body"],
                    names_by_wa_id.get(message["from"], ""),
                )


def extract_statuses(payload):
    """Yields (wamid, status, error_detail) for each delivery-status update
    (sent/delivered/read/failed) in a webhook payload — separate from
    extract_messages, since Meta puts these under "statuses", not "messages"."""
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for status_update in value.get("statuses", []):
                wamid = status_update.get("id")
                status = status_update.get("status")
                if not wamid or not status:
                    continue
                errors = status_update.get("errors") or []
                error_detail = "; ".join(
                    f"{error.get('code')}: {error.get('title')}" for error in errors
                )
                yield wamid, status, error_detail


def extract_non_text_messages(payload):
    """Yields (phone_number_id, from_wa_id, message_id, message_type) for each inbound
    message the AI can't handle (image, audio, video, document, sticker, location,
    contacts, etc.) — these get escalated to a human instead of an AI reply."""
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            for message in value.get("messages", []):
                if message.get("type") == "text":
                    continue
                yield (
                    phone_number_id,
                    message["from"],
                    message["id"],
                    message.get("type", "unknown"),
                )
