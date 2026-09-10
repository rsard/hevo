from abc import ABC, abstractmethod


class CalendarProvider(ABC):
    """Abstract interface for external calendar providers (e.g. Google Calendar)."""

    @abstractmethod
    def create_event(self, *, connection, title, start, end, description=""):
        """Creates an event on the external calendar and returns its event id."""

    @abstractmethod
    def delete_event(self, *, connection, event_id):
        """Deletes an event from the external calendar."""

    @abstractmethod
    def list_events(self, *, connection, time_min, time_max, max_results=50):
        """Returns upcoming events as normalized dicts: id, title, start, end,
        is_all_day, day (date the event belongs to for grouping), location, html_link."""
