def extract_messages(payload):
    """Yields (phone_number_id, from_wa_id, message_id, text) for each inbound text
    message in a WhatsApp Cloud API webhook payload. Non-text messages (image,
    audio, status updates) are skipped for MVP."""
    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value', {})
            phone_number_id = value.get('metadata', {}).get('phone_number_id')
            for message in value.get('messages', []):
                if message.get('type') != 'text':
                    continue
                yield (
                    phone_number_id,
                    message['from'],
                    message['id'],
                    message['text']['body'],
                )
