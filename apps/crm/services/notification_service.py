from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse

from apps.crm.models import EmailLog
from apps.user.models import VenueMembership


class NotificationService:
    """Sends notifications to venue staff about lead events."""

    @staticmethod
    def notify_escalation(lead):
        """Emails all active venue members that a lead requested human attention."""
        recipients = list(
            VenueMembership.objects.filter(venue=lead.venue, is_active=True)
            .exclude(user__email='')
            .values_list('user__email', flat=True)
        )
        if not recipients:
            return

        who = lead.customer_name or lead.customer_phone
        subject = f'Atendimento humano solicitado — {who}'
        context = {
            'who': who,
            'lead': lead,
            'lead_url': f"{settings.SITE_URL}{reverse('crm:lead-detail', args=[lead.pk])}",
            # Email clients fetch images directly, outside the Django request
            # context, so this needs to be an absolute URL, not a static tag.
            'logo_url': f"{settings.SITE_URL}{static('branding/hevo_logo_white.png')}",
        }
        text_body = render_to_string('crm/email/escalation_notification.txt', context)
        html_body = render_to_string('crm/email/escalation_notification.html', context)

        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        message.attach_alternative(html_body, 'text/html')
        message.send()

        EmailLog.objects.create(
            venue=lead.venue, subject=subject, recipient_count=len(recipients),
        )
