import re
import os
from datetime import datetime
from zoneinfo import ZoneInfo

EVENT_TITLE = re.compile(r"^(?P<name>.+?)\s+-\s+(?P<treatment>.+?)(?:\s+\((?P<session>\d+)\s*/\s*(?P<total>\d+)\))?$")
PHONE = re.compile(r"(?:Tel|Teléfono)\s*:\s*(\+?[\d\s()-]{8,})", re.IGNORECASE)


def parse_calendar_event(event: dict) -> dict:
    """Parsea el formato operativo del calendario; nunca interpreta notas clínicas."""
    title = (event.get("summary") or "").strip()
    match = EVENT_TITLE.match(title)
    start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
    phone_match = PHONE.search(event.get("description") or "")
    parsed_start = datetime.fromisoformat(start.replace("Z", "+00:00")) if start else None
    if parsed_start and parsed_start.tzinfo:
        parsed_start = parsed_start.astimezone(ZoneInfo(os.getenv("TIMEZONE", "America/Santiago"))).replace(tzinfo=None)
    parsed = {
        "name": match.group("name").strip() if match else title or "Cita sin nombre",
        "treatment": match.group("treatment").strip() if match else "Por confirmar",
        "session_number": int(match.group("session")) if match and match.group("session") else None,
        "session_total": int(match.group("total")) if match and match.group("total") else None,
        "phone": re.sub(r"[\s()-]", "", phone_match.group(1)) if phone_match else None,
        "starts_at": parsed_start if start and "T" in start else datetime.fromisoformat(start) if start else None,
        "cancelled": event.get("status") == "cancelled",
        "calendar_event_id": event.get("id"),
        "requires_attention": not bool(phone_match),
    }
    return parsed


def parse_whatsapp_reply(body: str) -> str:
    value = " ".join((body or "").strip().lower().split())
    if value in {"stop", "baja", "no quiero recibir más mensajes", "no quiero recibir mas mensajes", "parar"}:
        return "stop"
    if value in {"1", "sí", "si", "ok", "confirmo", "confirmar", "yes", "acepto"}:
        return "confirm"
    if value in {"2", "no puedo", "cancelar", "reprogramar", "cambiar", "mover"}:
        return "reschedule"
    return "unknown"
