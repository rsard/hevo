from apps.conversation.models import Conversation, Message


class ConversationService:
    """Helpers for creating conversations and recording messages on them."""

    @staticmethod
    def get_or_create_conversation(*, venue, external_contact_id, channel=Conversation.Channel.WHATSAPP):
        """Gets or creates the conversation for a venue and external contact on a channel."""
        conversation, _ = Conversation.objects.get_or_create(
            venue=venue, channel=channel, external_contact_id=external_contact_id,
        )
        return conversation

    @staticmethod
    def record_message(*, conversation, direction, sender_type, content, external_message_id=''):
        """Creates a message on a conversation and updates its last-message timestamp."""
        message = Message.objects.create(
            conversation=conversation,
            direction=direction,
            sender_type=sender_type,
            content=content,
            external_message_id=external_message_id,
        )
        conversation.last_message_at = message.created_at
        conversation.save(update_fields=['last_message_at', 'updated_at'])
        return message

    @staticmethod
    def get_or_create_inbound_message(*, conversation, sender_type, content, external_message_id):
        """Idempotent on external_message_id, backed by a DB unique constraint.

        Safe to call again for the same external_message_id — from a redelivered
        webhook or from a Celery retry re-running the task from the top.
        """
        message, created = Message.objects.get_or_create(
            conversation=conversation,
            external_message_id=external_message_id,
            defaults={
                'direction': Message.Direction.INBOUND,
                'sender_type': sender_type,
                'content': content,
            },
        )
        if created:
            conversation.last_message_at = message.created_at
            conversation.save(update_fields=['last_message_at', 'updated_at'])
        return message, created

    @staticmethod
    def get_history(conversation, limit=20):
        """Most recent messages, oldest first, formatted as LLM chat messages."""
        role_by_sender = {
            Message.SenderType.CUSTOMER: 'user',
            Message.SenderType.AI: 'assistant',
            Message.SenderType.HUMAN: 'assistant',
        }
        recent = conversation.messages.order_by('-created_at')[:limit]
        return [
            {'role': role_by_sender[message.sender_type], 'content': message.content}
            for message in reversed(recent)
        ]
