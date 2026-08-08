from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404

from apps.user.services import get_active_venue


class VenueScopedViewMixin(LoginRequiredMixin):
    """For CBVs operating on TenantModel subclasses.

    Resolves the logged-in user's venue once per request, scopes get_queryset()
    to it, and stamps it onto new instances in form_valid().
    """

    def dispatch(self, request, *args, **kwargs):
        """Resolve the user's active venue or 404 if they have none."""
        self.venue = get_active_venue(request.user)
        if self.venue is None:
            raise Http404('Nenhum espaço associado a este usuário.')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Scope the base queryset to the current venue only."""
        return super().get_queryset().filter(venue=self.venue)

    def form_valid(self, form):
        """Stamp the current venue onto the form instance before saving."""
        if hasattr(form, 'instance'):
            form.instance.venue = self.venue
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add the current venue to the template context."""
        context = super().get_context_data(**kwargs)
        context['venue'] = self.venue
        return context
