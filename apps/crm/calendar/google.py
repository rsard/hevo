import datetime as dt

from django.conf import settings
from django.utils import timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from apps.crm.calendar.base import CalendarProvider


class GoogleCalendarProvider(CalendarProvider):
    def _client(self, connection):
        expiry = connection.token_expires_at
        if timezone.is_aware(expiry):
            expiry = expiry.astimezone(dt.timezone.utc).replace(tzinfo=None)
        credentials = Credentials(
            token=connection.access_token,
            refresh_token=connection.refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            expiry=expiry,
        )
        return build('calendar', 'v3', credentials=credentials), credentials

    def _persist_if_refreshed(self, connection, credentials):
        """google-auth refreshes the in-memory Credentials transparently on an
        expired token; nothing writes that back to the DB unless we do it here."""
        if credentials.token == connection.access_token:
            return
        connection.access_token = credentials.token
        if credentials.expiry:
            connection.token_expires_at = credentials.expiry.replace(tzinfo=dt.timezone.utc)
        connection.save(update_fields=['access_token', 'token_expires_at', 'updated_at'])

    def create_event(self, *, connection, title, start, end, description=''):
        service, credentials = self._client(connection)
        event = service.events().insert(
            calendarId=connection.calendar_id,
            body={
                'summary': title,
                'description': description,
                'start': {'dateTime': start.isoformat()},
                'end': {'dateTime': end.isoformat()},
            },
        ).execute()
        self._persist_if_refreshed(connection, credentials)
        return event['id']

    def delete_event(self, *, connection, event_id):
        service, credentials = self._client(connection)
        service.events().delete(calendarId=connection.calendar_id, eventId=event_id).execute()
        self._persist_if_refreshed(connection, credentials)

    def list_events(self, *, connection, time_min, time_max, max_results=50):
        service, credentials = self._client(connection)
        response = service.events().list(
            calendarId=connection.calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=max_results,
        ).execute()
        self._persist_if_refreshed(connection, credentials)

        events = []
        for item in response.get('items', []):
            start_raw = item.get('start', {})
            end_raw = item.get('end', {})
            is_all_day = 'date' in start_raw

            if is_all_day:
                start_value = dt.datetime.strptime(start_raw['date'], '%Y-%m-%d').date()
                end_value = dt.datetime.strptime(end_raw['date'], '%Y-%m-%d').date()
                day = start_value
            else:
                start_value = timezone.localtime(dt.datetime.fromisoformat(start_raw['dateTime']))
                end_value = timezone.localtime(dt.datetime.fromisoformat(end_raw['dateTime']))
                day = start_value.date()

            events.append({
                'id': item.get('id'),
                'title': item.get('summary') or '(Sem título)',
                'start': start_value,
                'end': end_value,
                'is_all_day': is_all_day,
                'day': day,
                'location': item.get('location', ''),
                'html_link': item.get('htmlLink', ''),
            })
        return events
