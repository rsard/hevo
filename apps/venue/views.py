from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.core.views import VenueScopedViewMixin
from apps.user.services import get_active_venue
from apps.venue.forms import (
    DecorationOptionForm,
    DocumentForm,
    EventTypeForm,
    FAQForm,
    ImageForm,
    MenuForm,
    MenuItemFormSet,
    OpeningHoursFormSet,
    PackageForm,
    VenueProfileForm,
)
from apps.venue.models import (
    DecorationOption,
    Document,
    EventType,
    FAQ,
    Image,
    Menu,
    OpeningHours,
    Package,
)


@login_required
def profile_edit(request):
    """Edit the logged-in user's active venue profile.

    Staff users with no active venue are redirected to the backoffice customer list;
    other users with no venue get a 404.
    """
    venue = get_active_venue(request.user)
    if venue is None:
        if request.user.is_staff:
            return redirect('backoffice:customer-list')
        raise Http404('Nenhum espaço associado a este usuário.')

    if request.method == 'POST':
        form = VenueProfileForm(request.POST, instance=venue)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil do espaço atualizado.')
            return redirect('venue:profile')
    else:
        form = VenueProfileForm(instance=venue)

    return render(request, 'venue/profile_form.html', {'venue': venue, 'form': form})


@login_required
def opening_hours_edit(request):
    """Edit the active venue's weekly opening hours.

    Ensures an OpeningHours row exists for every weekday before building the formset.
    """
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    for weekday, _ in OpeningHours.Weekday.choices:
        OpeningHours.objects.get_or_create(venue=venue, weekday=weekday)
    queryset = OpeningHours.objects.filter(venue=venue).order_by('weekday')

    if request.method == 'POST':
        formset = OpeningHoursFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Horários atualizados.')
            return redirect('venue:opening-hours')
    else:
        formset = OpeningHoursFormSet(queryset=queryset)

    return render(request, 'venue/opening_hours_form.html', {'venue': venue, 'formset': formset})


class EventTypeListView(VenueScopedViewMixin, ListView):
    model = EventType
    template_name = 'venue/event_type_list.html'
    context_object_name = 'items'


class EventTypeCreateView(VenueScopedViewMixin, CreateView):
    model = EventType
    form_class = EventTypeForm
    template_name = 'venue/event_type_form.html'
    success_url = reverse_lazy('venue:event-type-list')


class EventTypeUpdateView(VenueScopedViewMixin, UpdateView):
    model = EventType
    form_class = EventTypeForm
    template_name = 'venue/event_type_form.html'
    success_url = reverse_lazy('venue:event-type-list')


class EventTypeDeleteView(VenueScopedViewMixin, DeleteView):
    model = EventType
    template_name = 'venue/confirm_delete.html'
    success_url = reverse_lazy('venue:event-type-list')


class PackageFormMixin:
    """Restricts a Package form's event type choices to the current venue's event types."""

    def get_form(self, form_class=None):
        """Return the form with its event_type field scoped to the current venue."""
        form = super().get_form(form_class)
        form.fields['event_type'].queryset = EventType.objects.filter(venue=self.venue)
        return form


class PackageListView(VenueScopedViewMixin, ListView):
    """Lists packages for the active venue, with event type preloaded."""

    model = Package
    template_name = 'venue/package_list.html'
    context_object_name = 'items'

    def get_queryset(self):
        """Return the venue's packages with event_type preloaded to avoid extra queries."""
        return super().get_queryset().select_related('event_type')


class PackageCreateView(VenueScopedViewMixin, PackageFormMixin, CreateView):
    model = Package
    form_class = PackageForm
    template_name = 'venue/package_form.html'
    success_url = reverse_lazy('venue:package-list')


class PackageUpdateView(VenueScopedViewMixin, PackageFormMixin, UpdateView):
    model = Package
    form_class = PackageForm
    template_name = 'venue/package_form.html'
    success_url = reverse_lazy('venue:package-list')


class PackageDeleteView(VenueScopedViewMixin, DeleteView):
    model = Package
    template_name = 'venue/confirm_delete.html'
    success_url = reverse_lazy('venue:package-list')


class DecorationOptionListView(VenueScopedViewMixin, ListView):
    model = DecorationOption
    template_name = 'venue/decoration_list.html'
    context_object_name = 'items'


class DecorationOptionCreateView(VenueScopedViewMixin, CreateView):
    model = DecorationOption
    form_class = DecorationOptionForm
    template_name = 'venue/decoration_form.html'
    success_url = reverse_lazy('venue:decoration-list')


class DecorationOptionUpdateView(VenueScopedViewMixin, UpdateView):
    model = DecorationOption
    form_class = DecorationOptionForm
    template_name = 'venue/decoration_form.html'
    success_url = reverse_lazy('venue:decoration-list')


class DecorationOptionDeleteView(VenueScopedViewMixin, DeleteView):
    model = DecorationOption
    template_name = 'venue/confirm_delete.html'
    success_url = reverse_lazy('venue:decoration-list')


class FAQListView(VenueScopedViewMixin, ListView):
    model = FAQ
    template_name = 'venue/faq_list.html'
    context_object_name = 'items'


class FAQCreateView(VenueScopedViewMixin, CreateView):
    model = FAQ
    form_class = FAQForm
    template_name = 'venue/faq_form.html'
    success_url = reverse_lazy('venue:faq-list')


class FAQUpdateView(VenueScopedViewMixin, UpdateView):
    model = FAQ
    form_class = FAQForm
    template_name = 'venue/faq_form.html'
    success_url = reverse_lazy('venue:faq-list')


class FAQDeleteView(VenueScopedViewMixin, DeleteView):
    model = FAQ
    template_name = 'venue/confirm_delete.html'
    success_url = reverse_lazy('venue:faq-list')


class ImageListView(VenueScopedViewMixin, ListView):
    model = Image
    template_name = 'venue/image_list.html'
    context_object_name = 'items'


class ImageCreateView(VenueScopedViewMixin, CreateView):
    model = Image
    form_class = ImageForm
    template_name = 'venue/image_form.html'
    success_url = reverse_lazy('venue:image-list')


class ImageUpdateView(VenueScopedViewMixin, UpdateView):
    model = Image
    form_class = ImageForm
    template_name = 'venue/image_form.html'
    success_url = reverse_lazy('venue:image-list')


class ImageDeleteView(VenueScopedViewMixin, DeleteView):
    model = Image
    template_name = 'venue/confirm_delete.html'
    success_url = reverse_lazy('venue:image-list')


class DocumentListView(VenueScopedViewMixin, ListView):
    model = Document
    template_name = 'venue/document_list.html'
    context_object_name = 'items'


class DocumentCreateView(VenueScopedViewMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'venue/document_form.html'
    success_url = reverse_lazy('venue:document-list')


class DocumentUpdateView(VenueScopedViewMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = 'venue/document_form.html'
    success_url = reverse_lazy('venue:document-list')


class DocumentDeleteView(VenueScopedViewMixin, DeleteView):
    model = Document
    template_name = 'venue/confirm_delete.html'
    success_url = reverse_lazy('venue:document-list')


@login_required
def menu_list(request):
    """List the active venue's menus with their items preloaded."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')
    menus = Menu.objects.filter(venue=venue).prefetch_related('items')
    return render(request, 'venue/menu_list.html', {'venue': venue, 'menus': menus})


@login_required
def menu_edit(request, pk=None):
    """Create or update a menu (when pk is given) along with its items formset."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')

    menu = get_object_or_404(Menu, pk=pk, venue=venue) if pk else Menu(venue=venue)

    if request.method == 'POST':
        form = MenuForm(request.POST, instance=menu)
        if form.is_valid():
            menu = form.save(commit=False)
            menu.venue = venue
            menu.save()
            formset = MenuItemFormSet(request.POST, instance=menu)
            if formset.is_valid():
                formset.save()
                messages.success(request, 'Cardápio salvo.')
                return redirect('venue:menu-list')
        else:
            formset = MenuItemFormSet(request.POST, instance=menu)
    else:
        form = MenuForm(instance=menu)
        formset = MenuItemFormSet(instance=menu)

    return render(request, 'venue/menu_form.html', {'venue': venue, 'form': form, 'formset': formset, 'menu': menu})


@login_required
def menu_delete(request, pk):
    """Delete a menu belonging to the active venue after POST confirmation."""
    venue = get_active_venue(request.user)
    if venue is None:
        raise Http404('Nenhum espaço associado a este usuário.')
    menu = get_object_or_404(Menu, pk=pk, venue=venue)
    if request.method == 'POST':
        menu.delete()
        messages.success(request, 'Cardápio removido.')
        return redirect('venue:menu-list')
    return render(request, 'venue/confirm_delete.html', {'object': menu})
