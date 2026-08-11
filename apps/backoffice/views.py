from functools import wraps
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.backoffice.forms import NewCustomerForm
from apps.backoffice.models import Subscription
from apps.crm.models import Lead
from apps.dashboard.views import WEEKS_TO_SHOW, _week_start, _weekly_series
from apps.user.models import User, VenueMembership
from apps.venue.models import Venue


def staff_required(view_func):
    """Decorator restricting a view to logged-in staff users, 404ing everyone else."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise Http404
        return view_func(request, *args, **kwargs)
    return wrapper


@staff_required
def platform_dashboard(request):
    """Staff-only view of platform-wide metrics: venues, subscriptions, leads, and trends."""
    today = timezone.localdate()
    venues = Venue.objects.select_related('subscription')

    active_subscriptions = venues.filter(subscription__status=Subscription.Status.ACTIVE).count()
    new_venues_30d = venues.filter(created_at__date__gte=today - timedelta(days=30)).count()

    leads = Lead.objects.all()
    won_count = leads.filter(stage=Lead.Stage.WON).count()
    lost_count = leads.filter(stage=Lead.Stage.LOST).count()
    closed_count = won_count + lost_count
    conversion_rate = round((won_count / closed_count) * 100, 1) if closed_count else None

    week_starts = [
        _week_start(today) - timedelta(weeks=i) for i in range(WEEKS_TO_SHOW - 1, -1, -1)
    ]
    weekly_leads = _weekly_series(
        leads.filter(created_at__date__gte=week_starts[0]).values_list('created_at', flat=True),
        week_starts,
    )

    venue_rows = [
        {
            'venue': venue,
            'lead_count': venue.lead_set.count(),
            'escalated_count': venue.lead_set.filter(escalated_at__isnull=False).count(),
        }
        for venue in venues.order_by('-created_at')
    ]

    context = {
        'total_venues': venues.count(),
        'active_subscriptions': active_subscriptions,
        'new_venues_30d': new_venues_30d,
        'total_leads': leads.count(),
        'escalated_count': leads.filter(escalated_at__isnull=False).count(),
        'conversion_rate': conversion_rate,
        'weekly_leads': weekly_leads,
        'venue_rows': venue_rows,
    }
    return render(request, 'backoffice/dashboard.html', context)


@staff_required
def customer_list(request):
    """Staff-only view listing all venues with their subscription and membership info."""
    venues = (
        Venue.objects.select_related('subscription')
        .prefetch_related('memberships__user')
        .order_by('-created_at')
    )
    return render(request, 'backoffice/customer_list.html', {'venues': venues})


@staff_required
def customer_detail(request, pk):
    """Staff-only view showing details for a single venue."""
    venue = get_object_or_404(
        Venue.objects.select_related('subscription').prefetch_related('memberships__user'),
        pk=pk,
    )
    return render(request, 'backoffice/customer_detail.html', {'venue': venue})


@staff_required
def customer_create(request):
    """Staff-only view to onboard a new venue, its owner user, and subscription at once."""
    if request.method == 'POST':
        form = NewCustomerForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                venue = Venue.objects.create(
                    name=form.cleaned_data['venue_name'],
                    slug=form.unique_slug(),
                    whatsapp_number=form.cleaned_data['venue_whatsapp_number'],
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
