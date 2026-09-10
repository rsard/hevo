import json
import logging

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.conversation.whatsapp.client import (
    create_message_template,
    get_phone_number_display,
    get_waba_phone_number_id,
    subscribe_app_to_waba,
)
from apps.core.views import VenueScopedViewMixin
from apps.user.services import get_active_venue
from apps.venue.forms import (
    DecorationOptionForm,
    EventTypeForm,
    FAQForm,
    MenuForm,
    MenuItemFormSet,
    OpeningHoursFormSet,
    PackageForm,
    VenueProfileForm,
)
from apps.venue.models import (
    DecorationOption,
    EventType,
    FAQ,
    Menu,
    OpeningHours,
    Package,
)

logger = logging.getLogger(__name__)


@login_required
def profile_edit(request):
    """Edit the logged-in user's active venue profile.

    Staff users with no active venue are redirected to the backoffice customer list;
    other users with no venue get a 404.
    """
    venue = get_active_venue(request.user)
    if venue is None:
        if request.user.is_staff:
            return redirect("backoffice:customer-list")
        raise Http404("Nenhum espaço associado a este usuário.")

    if request.method == "POST":
        form = VenueProfileForm(request.POST, instance=venue)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil do espaço atualizado.")
            return redirect("venue:profile")
    else:
        form = VenueProfileForm(instance=venue)

    return render(request, "venue/profile_form.html", {
        "venue": venue,
        "form": form,
    })


@login_required
@require_POST
def whatsapp_connect(request):
    """Completes Embedded Signup: after the venue authorizes Hevo in Meta's
    popup, the frontend posts here with the phone number/WABA it picked. We
    subscribe our app to that WABA's webhooks and store both IDs on the venue."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404("Nenhum espaço associado a este usuário.")

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Corpo da requisição inválido."}, status=400)

    phone_number_id = data.get("phone_number_id", "").strip()
    waba_id = data.get("waba_id", "").strip()
    if not waba_id:
        return JsonResponse({"error": "waba_id é obrigatório."}, status=400)

    try:
        if not phone_number_id:
            # Coexistence flow (existing WhatsApp Business App number): the
            # signup popup only returns the waba_id, so look up the number
            # that's already registered on it.
            phone_number_id = get_waba_phone_number_id(waba_id)
        subscribe_app_to_waba(waba_id)
    except requests.RequestException:
        logger.exception("Failed to connect WABA %s (venue %s)", waba_id, venue.id)
        return JsonResponse(
            {"error": "Não foi possível concluir a conexão com o WhatsApp. Tente novamente."},
            status=502,
        )

    if not phone_number_id:
        return JsonResponse(
            {"error": "Nenhum número de telefone encontrado nessa conta do WhatsApp."}, status=400,
        )

    _ensure_default_templates(waba_id)

    venue.whatsapp_phone_number_id = phone_number_id
    venue.whatsapp_business_account_id = waba_id
    venue.whatsapp_connected_number = get_phone_number_display(phone_number_id)
    venue.save(update_fields=[
        "whatsapp_phone_number_id", "whatsapp_business_account_id", "whatsapp_connected_number",
    ])
    return JsonResponse({"status": "connected"})


@login_required
def whatsapp_disconnect(request):
    """Removes the venue's WhatsApp connection (local only — doesn't revoke
    anything on Meta's side, same as calendar_disconnect for Google Calendar)."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404("Nenhum espaço associado a este usuário.")
    if request.method == "POST":
        venue.whatsapp_phone_number_id = None
        venue.whatsapp_business_account_id = ""
        venue.whatsapp_connected_number = ""
        venue.save(update_fields=[
            "whatsapp_phone_number_id", "whatsapp_business_account_id", "whatsapp_connected_number",
        ])
        messages.success(request, "WhatsApp desconectado.")
    return redirect("crm:integration-settings")


def _ensure_default_templates(waba_id):
    """Creates the templates Hevo depends on (follow-ups, visit reminders) on a
    newly connected WABA. Best-effort — a template that already exists (e.g. a
    venue reconnecting) or gets rejected shouldn't block the connection itself,
    just leave that automation dark until someone creates it by hand."""
    templates = [
        {
            "name": settings.WHATSAPP_FOLLOWUP_TEMPLATE_NAME,
            "category": "MARKETING",
            "language": settings.WHATSAPP_FOLLOWUP_TEMPLATE_LANGUAGE,
            "body_text": settings.WHATSAPP_FOLLOWUP_TEMPLATE_TEXT,
        },
        {
            "name": settings.WHATSAPP_VISIT_REMINDER_TEMPLATE_NAME,
            "category": "UTILITY",
            "language": settings.WHATSAPP_VISIT_REMINDER_TEMPLATE_LANGUAGE,
            "body_text": settings.WHATSAPP_VISIT_REMINDER_TEMPLATE_BODY,
            "body_example": ["Espaço Exemplo", "18/08 às 15:00"],
        },
    ]
    for template in templates:
        try:
            create_message_template(waba_id, **template)
        except requests.RequestException:
            logger.info(
                "Could not create template %s on WABA %s (may already exist)",
                template["name"], waba_id,
            )


@login_required
def opening_hours_edit(request):
    """Edit the active venue's weekly opening hours.

    Ensures an OpeningHours row exists for every weekday before building the formset.
    """
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404("Nenhum espaço associado a este usuário.")

    for weekday, _ in OpeningHours.Weekday.choices:
        OpeningHours.objects.get_or_create(venue=venue, weekday=weekday)
    queryset = OpeningHours.objects.filter(venue=venue).order_by("weekday")

    if request.method == "POST":
        formset = OpeningHoursFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Horários atualizados.")
            return redirect("venue:opening-hours")
    else:
        formset = OpeningHoursFormSet(queryset=queryset)

    return render(request, "venue/opening_hours_form.html", {"venue": venue, "formset": formset})


class EventTypeListView(VenueScopedViewMixin, ListView):
    model = EventType
    template_name = "venue/event_type_list.html"
    context_object_name = "items"


class EventTypeCreateView(VenueScopedViewMixin, CreateView):
    model = EventType
    form_class = EventTypeForm
    template_name = "venue/event_type_form.html"
    success_url = reverse_lazy("venue:event-type-list")


class EventTypeUpdateView(VenueScopedViewMixin, UpdateView):
    model = EventType
    form_class = EventTypeForm
    template_name = "venue/event_type_form.html"
    success_url = reverse_lazy("venue:event-type-list")


class EventTypeDeleteView(VenueScopedViewMixin, DeleteView):
    model = EventType
    template_name = "venue/confirm_delete.html"
    success_url = reverse_lazy("venue:event-type-list")
    extra_context = {"section_title": "Base de Conhecimento", "nav_template": "venue/_knowledge_base_nav.html"}


class PackageFormMixin:
    """Restricts a Package form's event type choices to the current venue's event types."""

    def get_form(self, form_class=None):
        """Return the form with its event_type field scoped to the current venue."""
        form = super().get_form(form_class)
        form.fields["event_type"].queryset = EventType.objects.filter(venue=self.venue)
        return form


class PackageListView(VenueScopedViewMixin, ListView):
    """Lists packages for the active venue, with event type preloaded."""

    model = Package
    template_name = "venue/package_list.html"
    context_object_name = "items"

    def get_queryset(self):
        """Return the venue's packages with event_type preloaded to avoid extra queries."""
        return super().get_queryset().select_related("event_type")


class PackageCreateView(VenueScopedViewMixin, PackageFormMixin, CreateView):
    model = Package
    form_class = PackageForm
    template_name = "venue/package_form.html"
    success_url = reverse_lazy("venue:package-list")


class PackageUpdateView(VenueScopedViewMixin, PackageFormMixin, UpdateView):
    model = Package
    form_class = PackageForm
    template_name = "venue/package_form.html"
    success_url = reverse_lazy("venue:package-list")


class PackageDeleteView(VenueScopedViewMixin, DeleteView):
    model = Package
    template_name = "venue/confirm_delete.html"
    success_url = reverse_lazy("venue:package-list")
    extra_context = {"section_title": "Base de Conhecimento", "nav_template": "venue/_knowledge_base_nav.html"}


class DecorationOptionListView(VenueScopedViewMixin, ListView):
    model = DecorationOption
    template_name = "venue/decoration_list.html"
    context_object_name = "items"


class DecorationOptionCreateView(VenueScopedViewMixin, CreateView):
    model = DecorationOption
    form_class = DecorationOptionForm
    template_name = "venue/decoration_form.html"
    success_url = reverse_lazy("venue:decoration-list")


class DecorationOptionUpdateView(VenueScopedViewMixin, UpdateView):
    model = DecorationOption
    form_class = DecorationOptionForm
    template_name = "venue/decoration_form.html"
    success_url = reverse_lazy("venue:decoration-list")


class DecorationOptionDeleteView(VenueScopedViewMixin, DeleteView):
    model = DecorationOption
    template_name = "venue/confirm_delete.html"
    success_url = reverse_lazy("venue:decoration-list")
    extra_context = {"section_title": "Base de Conhecimento", "nav_template": "venue/_knowledge_base_nav.html"}


class FAQListView(VenueScopedViewMixin, ListView):
    model = FAQ
    template_name = "venue/faq_list.html"
    context_object_name = "items"


class FAQCreateView(VenueScopedViewMixin, CreateView):
    model = FAQ
    form_class = FAQForm
    template_name = "venue/faq_form.html"
    success_url = reverse_lazy("venue:faq-list")


class FAQUpdateView(VenueScopedViewMixin, UpdateView):
    model = FAQ
    form_class = FAQForm
    template_name = "venue/faq_form.html"
    success_url = reverse_lazy("venue:faq-list")


class FAQDeleteView(VenueScopedViewMixin, DeleteView):
    model = FAQ
    template_name = "venue/confirm_delete.html"
    success_url = reverse_lazy("venue:faq-list")
    extra_context = {"section_title": "Base de Conhecimento", "nav_template": "venue/_knowledge_base_nav.html"}


@login_required
def menu_list(request):
    """List the active venue's menus with their items preloaded."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404("Nenhum espaço associado a este usuário.")
    menus = Menu.objects.filter(venue=venue).prefetch_related("items")
    return render(request, "venue/menu_list.html", {"venue": venue, "menus": menus})


@login_required
def menu_edit(request, pk=None):
    """Create or update a menu (when pk is given) along with its items formset."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404("Nenhum espaço associado a este usuário.")

    menu = get_object_or_404(Menu, pk=pk, venue=venue) if pk else Menu(venue=venue)

    if request.method == "POST":
        form = MenuForm(request.POST, instance=menu)
        if form.is_valid():
            menu = form.save(commit=False)
            menu.venue = venue
            menu.save()
            formset = MenuItemFormSet(request.POST, instance=menu)
            if formset.is_valid():
                formset.save()
                messages.success(request, "Cardápio salvo.")
                return redirect("venue:menu-list")
        else:
            formset = MenuItemFormSet(request.POST, instance=menu)
    else:
        form = MenuForm(instance=menu)
        formset = MenuItemFormSet(instance=menu)

    return render(request, "venue/menu_form.html", {"venue": venue, "form": form, "formset": formset, "menu": menu})


@login_required
def menu_delete(request, pk):
    """Delete a menu belonging to the active venue after POST confirmation."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404("Nenhum espaço associado a este usuário.")
    menu = get_object_or_404(Menu, pk=pk, venue=venue)
    if request.method == "POST":
        menu.delete()
        messages.success(request, "Cardápio removido.")
        return redirect("venue:menu-list")
    return render(request, "venue/confirm_delete.html", {
        "object": menu,
        "section_title": "Base de Conhecimento",
        "nav_template": "venue/_knowledge_base_nav.html",
    })
