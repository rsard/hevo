from django.urls import path

from apps.conversation.whatsapp.webhook import whatsapp_webhook

app_name = 'conversation'

urlpatterns = [
    path('whatsapp/webhook/', whatsapp_webhook, name='whatsapp-webhook'),
]
