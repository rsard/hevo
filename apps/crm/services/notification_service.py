from django.conf import settings
from django.core.mail import send_mail

from apps.user.models import VenueMembership


class NotificationService:
    @staticmethod
    def notify_escalation(lead):
        recipients = list(
            VenueMembership.objects.filter(venue=lead.venue, is_active=True)
            .exclude(user__email='')
            .values_list('user__email', flat=True)
        )
        if not recipients:
            return

        who = lead.customer_name or lead.customer_phone
        subject = f'[Hevo] Atendimento humano solicitado — {who}'
        body = (
            f'{who} pediu para falar com uma pessoa da equipe.\n\n'
            f'Resumo: {lead.conversation_summary or "Sem resumo disponível."}\n\n'
            f'Ver conversa: {settings.SITE_URL}/crm/leads/{lead.pk}/'
        )
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
        )
