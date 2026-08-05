from django.contrib import admin

from apps.conversation.models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('direction', 'sender_type', 'content', 'created_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('external_contact_id', 'venue', 'channel', 'status', 'last_message_at')
    list_filter = ('venue', 'channel', 'status')
    inlines = [MessageInline]
