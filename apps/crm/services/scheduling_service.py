from datetime import datetime, timedelta

from apps.crm.calendar import GoogleCalendarProvider
from apps.crm.models import Lead, Visit
from apps.crm.services.crm_service import CRMService
from apps.venue.models import OpeningHours

VISIT_DURATION = timedelta(hours=1)


class SchedulingService:
    """Checks venue availability and books visits, syncing with the connected calendar."""

    @staticmethod
    def is_available(*, venue, start):
        """Returns whether a 1-hour visit slot is free: within opening hours, no
        conflicting visit, and no clash on the connected external calendar."""
        end = start + VISIT_DURATION
        try:
            hours = venue.opening_hours.get(weekday=start.weekday())
        except OpeningHours.DoesNotExist:
            return False
        if hours.is_closed or not hours.opens_at or not hours.closes_at:
            return False
        if not (hours.opens_at <= start.time() < hours.closes_at):
            return False

        conflicts = Visit.objects.filter(
            venue=venue,
            status__in=[Visit.Status.SCHEDULED, Visit.Status.CONFIRMED],
            scheduled_at__lt=end,
            scheduled_at__gte=start - VISIT_DURATION,
        )
        if conflicts.exists():
            return False

        connection = getattr(venue, 'calendar_connection', None)
        if connection:
            events = GoogleCalendarProvider().list_events(
                connection=connection, time_min=start, time_max=end,
            )
            for event in events:
                if event['is_all_day']:
                    if event['start'] <= start.date() < event['end']:
                        return False
                elif event['end'] > start and event['start'] < end:
                    return False

        return True

    @staticmethod
    def suggest_alternative_slots(*, venue, after, count=3, horizon_days=14):
        """Naive suggestion: proposes the venue's daily opening time, walking forward
        day by day. Good enough for MVP; a real slot grid can replace this later."""
        suggestions = []
        day = after.date()
        for _ in range(horizon_days):
            day += timedelta(days=1)
            hours = venue.opening_hours.filter(weekday=day.weekday(), is_closed=False).first()
            if not hours or not hours.opens_at:
                continue
            candidate = datetime.combine(day, hours.opens_at, tzinfo=after.tzinfo)
            if SchedulingService.is_available(venue=venue, start=candidate):
                suggestions.append(candidate)
            if len(suggestions) >= count:
                break
        return suggestions

    @staticmethod
    def schedule_visit(*, lead, start, notes=''):
        """Books a visit for the lead, creates the calendar event if connected, and
        advances the lead to Visit Scheduled."""
        if not SchedulingService.is_available(venue=lead.venue, start=start):
            raise ValueError('Requested time is not available.')

        visit = Visit.objects.create(venue=lead.venue, lead=lead, scheduled_at=start, notes=notes)

        connection = getattr(lead.venue, 'calendar_connection', None)
        if connection:
            event_id = GoogleCalendarProvider().create_event(
                connection=connection,
                title=f'Visita - {lead.customer_name or lead.customer_phone}',
                start=start,
                end=start + VISIT_DURATION,
                description=notes,
            )
            visit.calendar_event_id = event_id
            visit.save(update_fields=['calendar_event_id'])

        CRMService.update_stage(lead=lead, stage=Lead.Stage.NEGOTIATION)
        return visit
