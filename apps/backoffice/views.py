from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.backoffice.forms import NewCustomerForm
from apps.backoffice.models import Subscription
from apps.user.models import User, VenueMembership
from apps.venue.models import Venue


def staff_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise Http404
        return view_func(request, *args, **kwargs)
    return wrapper


@staff_required
def customer_list(request):
    venues = (
        Venue.objects.select_related('subscription')
        .prefetch_related('memberships__user')
        .order_by('-created_at')
    )
    return render(request, 'backoffice/customer_list.html', {'venues': venues})


@staff_required
def customer_detail(request, pk):
    venue = get_object_or_404(
        Venue.objects.select_related('subscription').prefetch_related('memberships__user'),
        pk=pk,
    )
    return render(request, 'backoffice/customer_detail.html', {'venue': venue})


@staff_required
def customer_create(request):
    if request.method == 'POST':
        form = NewCustomerForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                venue = Venue.objects.create(
                    name=form.cleaned_data['venue_name'],
                    slug=form.unique_slug(),
                    whatsapp_number=form.cleaned_data['venue_whatsapp_number'],
                    whatsapp_phone_number_id=form.cleaned_data['venue_whatsapp_phone_number_id'] or None,
                )
                user = User.objects.create_user(
                    username=form.cleaned_data['owner_username'],
                    email=form.cleaned_data['owner_email'],
                    password=form.cleaned_data['owner_password'],
                )
                VenueMembership.objects.create(user=user, venue=venue, role=VenueMembership.Role.OWNER)
                Subscription.objects.create(
                    venue=venue,
                    plan_name=form.cleaned_data['plan_name'],
                    monthly_price=form.cleaned_data['monthly_price'],
                    status=form.cleaned_data['status'],
                    started_at=form.cleaned_data['started_at'],
                    notes=form.cleaned_data['notes'],
                )
            messages.success(request, f'Cliente "{venue.name}" criado com sucesso.')
            return redirect('backoffice:customer-list')
    else:
        form = NewCustomerForm()
    return render(request, 'backoffice/customer_form.html', {'form': form})
