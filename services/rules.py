from datetime import datetime, timedelta
from services.time import now_local


def followup_stage(last_completed_session: datetime | None, has_future_appointment: bool, now: datetime | None = None) -> int | None:
    """Devuelve día de seguimiento 3, 7 o 14; 14 marca el umbral de riesgo."""
    if not last_completed_session or has_future_appointment:
        return None
    now = now or now_local()
    days = (now.date() - last_completed_session.date()).days
    if days >= 14:
        return 14
    if days >= 7:
        return 7
    if days >= 3:
        return 3
    return None


def is_waitlist_compatible(entry, appointment) -> bool:
    """Compatibilidad conservadora por tratamiento y preferencias de día/hora."""
    if entry.status != "waiting":
        return False
    if entry.treatment and appointment.treatment and entry.treatment.casefold() != appointment.treatment.casefold():
        return False
    preferred = entry.preferred_times or ""
    if preferred:
        day_names = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
        day = appointment.starts_at.weekday()
        if not any(day_names[day] in token.strip().casefold() for token in preferred.split(",")):
            return False
    return True
