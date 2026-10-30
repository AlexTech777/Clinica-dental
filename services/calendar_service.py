import logging
from datetime import datetime, timedelta
import hashlib
import os
from zoneinfo import ZoneInfo

from .parsers import parse_calendar_event

log = logging.getLogger(__name__)


class GoogleCalendarService:
    def __init__(self, service_account_file: str | None, calendar_id: str | None, dry_run: bool = True):
        self.service_account_file = service_account_file
        self.calendar_id = calendar_id
        self.dry_run = dry_run
        self._service = None

    @property
    def configured(self):
        return bool(self.calendar_id and self.service_account_file)

    @property
    def connected(self):
        return self.configured

    def _client(self):
        if not self.configured:
            raise RuntimeError("Google Calendar no está configurado")
        if self._service is None:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=["https://www.googleapis.com/auth/calendar"],
            )
            self._service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        return self._service

    def create_event(self, appointment, patient):
        if not self.connected:
            return None
        title = f"{patient.name} - {appointment.treatment}"
        if appointment.session_number and appointment.session_total:
            title += f" ({appointment.session_number}/{appointment.session_total})"
        start = appointment.starts_at
        event_id = hashlib.sha256(f"sonrisa-clara:{appointment.id}".encode()).hexdigest()[:32]
        body = {
            "id": event_id,
            "summary": title,
            "description": f"Tel: {patient.phone}",
            "start": {"dateTime": start.isoformat(), "timeZone": "America/Santiago"},
            "end": {"dateTime": (start + timedelta(minutes=appointment.duration_minutes)).isoformat(), "timeZone": "America/Santiago"},
            "extendedProperties": {"private": {"dental_app": "sonrisa-clara", "appointment_id": str(appointment.id)}},
        }
        client = self._client()
        try:
            return client.events().insert(calendarId=self.calendar_id, body=body).execute()["id"]
        except Exception as exc:
            if getattr(exc, "resp", None) is not None and exc.resp.status == 409:
                return client.events().get(calendarId=self.calendar_id, eventId=event_id).execute()["id"]
            raise

    def update_event(self, appointment, patient):
        if not self.connected or not appointment.calendar_event_id:
            return self.create_event(appointment, patient)
        title = f"{patient.name} - {appointment.treatment}"
        if appointment.session_number and appointment.session_total:
            title += f" ({appointment.session_number}/{appointment.session_total})"
        start = appointment.starts_at
        zone = os.getenv("TIMEZONE", "America/Santiago")
        body = {"summary": title, "description": f"Tel: {patient.phone}",
            "start": {"dateTime": start.isoformat(), "timeZone": zone},
            "end": {"dateTime": (start + timedelta(minutes=appointment.duration_minutes)).isoformat(), "timeZone": zone}}
        return self._client().events().patch(calendarId=self.calendar_id, eventId=appointment.calendar_event_id, body=body).execute()["id"]

    def list_events(self, time_min: datetime | None = None, time_max: datetime | None = None):
        if not self.connected:
            return []
        params = {"calendarId": self.calendar_id, "singleEvents": True, "orderBy": "startTime", "maxResults": 2500}
        if time_min:
            zone = ZoneInfo(os.getenv("TIMEZONE", "America/Santiago"))
            params["timeMin"] = time_min.replace(tzinfo=zone).isoformat() if time_min.tzinfo is None else time_min.astimezone(zone).isoformat()
        if time_max:
            zone = ZoneInfo(os.getenv("TIMEZONE", "America/Santiago"))
            params["timeMax"] = time_max.replace(tzinfo=zone).isoformat() if time_max.tzinfo is None else time_max.astimezone(zone).isoformat()
        return self._client().events().list(**params).execute().get("items", [])

    def cancel_event(self, event_id: str):
        if self.connected and event_id:
            self._client().events().delete(calendarId=self.calendar_id, eventId=event_id).execute()

    @staticmethod
    def parse_event(event: dict):
        return parse_calendar_event(event)
