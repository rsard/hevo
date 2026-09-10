from io import BytesIO

from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa

from apps.conversation.models import Conversation, Message
from apps.conversation.services import ConversationService
from apps.conversation.whatsapp.client import WhatsAppClient
from apps.core.utils import format_currency
from apps.crm.models import LeadActivity, Proposal
from apps.crm.services.crm_service import CRMService


class ProposalService:
    """Generates pricing proposals as PDFs and sends them to a lead over WhatsApp."""

    @staticmethod
    def render_pdf(*, lead, package, price, notes):
        """Renders the proposal template to PDF bytes. Used both for the owner's
        in-browser preview and for the file that actually gets sent."""
        html = render_to_string("crm/proposal/proposal_pdf.html", {
            "lead": lead,
            "venue": lead.venue,
            "package": package,
            "price": price,
            "notes": notes,
            "today": timezone.localdate(),
        })
        buffer = BytesIO()
        pisa.CreatePDF(html, dest=buffer)
        return buffer.getvalue()

    @staticmethod
    def send(*, lead, package, price, notes):
        """Generates the final PDF, records it, and sends it to the lead's WhatsApp."""
        pdf_bytes = ProposalService.render_pdf(lead=lead, package=package, price=price, notes=notes)

        proposal = Proposal.objects.create(
            venue=lead.venue, lead=lead, package=package, price=price, notes=notes,
        )
        filename = f"proposta-{lead.pk}-{proposal.pk}.pdf"
        proposal.pdf.save(filename, ContentFile(pdf_bytes), save=False)

        conversation = lead.conversation
        if conversation.channel == Conversation.Channel.WHATSAPP:
            client = WhatsAppClient(lead.venue.whatsapp_phone_number_id)
            media_id = client.upload_media(
                file_bytes=pdf_bytes, filename=filename, mime_type="application/pdf",
            )
            client.send_document(
                to=conversation.external_contact_id,
                media_id=media_id,
                filename=filename,
                caption="Segue nossa proposta! Qualquer dúvida, é só chamar.",
            )

        proposal.sent_at = timezone.now()
        proposal.save(update_fields=["pdf", "sent_at"])

        ConversationService.record_message(
            conversation=conversation,
            direction=Message.Direction.OUTBOUND,
            sender_type=Message.SenderType.HUMAN,
            content=f"[Proposta enviada: {package.name} — {format_currency(price)}]",
        )
        CRMService.log_activity(
            lead=lead,
            activity_type=LeadActivity.ActivityType.HUMAN_ACTION,
            description=f"Proposta enviada: {package.name}, {format_currency(price)}.",
        )
        return proposal
