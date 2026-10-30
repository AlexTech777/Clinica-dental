import logging
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import Appointment, Patient, MessageLog, WaitlistEntry
from services.rules import followup_stage, is_waitlist_compatible
from services.time import now_local

log = logging.getLogger(__name__)


def within_message_window(now, start_hour, end_hour):
    return int(start_hour) <= now.hour < int(end_hour)


def safe_send(db, whatsapp, patient, key, body, category, appointment_id=None):
    if not patient or not patient.phone or patient.opted_out:
        return False
    record = db.scalar(select(MessageLog).where(MessageLog.idempotency_key == key))
    if record and record.status != "failed":
        return False
    if record:
        record.status = "sending"
    else:
        record = MessageLog(idempotency_key=key, patient_id=patient.id, appointment_id=appointment_id, category=category, status="sending")
        db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    try:
        sent = whatsapp.send(patient.phone, body, key)
        record.provider_id = sent.get("sid")
        record.status = "dry_run" if sent.get("dry_run") else "sent"
        patient.last_contact = now_local()
        db.commit()
        return True
    except Exception:
        log.exception("Fallo envío WhatsApp para registro %s", record.id)
        record.status = "failed"
        db.commit()
        return False


def offer_waitlist(db, appointment, whatsapp, assistant_phone):
    if not appointment or appointment.status != "released":
        return None
    entries = list(db.scalars(select(WaitlistEntry).where(WaitlistEntry.status == "waiting").order_by(WaitlistEntry.created_at, WaitlistEntry.id)))
    candidate = next((entry for entry in entries if is_waitlist_compatible(entry, appointment)), None)
    if not candidate:
        return None
    candidate.status = "contacted"
    candidate.released_appointment_id = appointment.id
    db.commit()
    if candidate.phone:
        key = f"waitlist:{candidate.id}:slot:{appointment.id}"
        existing = db.scalar(select(MessageLog).where(MessageLog.idempotency_key == key))
        if not existing:
            logrow = MessageLog(idempotency_key=key, patient_id=None, appointment_id=appointment.id, category="waitlist", status="sending")
            db.add(logrow)
            db.commit()
            try:
                result = whatsapp.send(candidate.phone, f"Se liberó un espacio para {appointment.starts_at:%d/%m a las %H:%M}. ¿Te sirve? Responde SÍ para solicitarlo o NO para dejarlo disponible.", key)
                logrow.provider_id = result.get("sid")
                logrow.status = "dry_run" if result.get("dry_run") else "sent"
                db.commit()
            except Exception:
                logrow.status = "failed"
                db.commit()
    if assistant_phone:
        whatsapp.send(assistant_phone, f"Espacio liberado: {appointment.starts_at:%d/%m %H:%M}. Se contactó a {candidate.name}, primera persona compatible en espera.", f"assistant-slot:{appointment.id}")
    return candidate


def run_automation_jobs(whatsapp, start_hour=9, end_hour=20):
    now = now_local()
    if not within_message_window(now, start_hour, end_hour):
        return
    db = SessionLocal()
    try:
        appointments = list(db.scalars(select(Appointment).where(
            Appointment.starts_at > now,
            Appointment.status.in_(["pending", "confirmed", "no_response"]),
            Appointment.attention_required.is_(False),
        )))
        for appointment in appointments:
            patient = appointment.patient
            if patient.opted_out or not patient.phone:
                continue
            hours_left = (appointment.starts_at - now).total_seconds() / 3600
            sent_keys = appointment.reminder_set()
            due_keys = []
            if 0 < hours_left <= 48 and "48h" not in sent_keys:
                due_keys.append("48h")
            if 0 < hours_left <= 3 and "3h" not in sent_keys:
                due_keys.append("3h")
            for due in due_keys:
                gentle = "Hola" if due == "48h" else "Hola de nuevo"
                body = f"{gentle}, te recordamos tu cita dental el {appointment.starts_at:%d/%m a las %H:%M}. Responde 1 para confirmar o 2 si necesitas reprogramar. Si prefieres no recibir mensajes, responde STOP."
                key = f"appointment:{appointment.id}:reminder:{due}"
                if safe_send(db, whatsapp, patient, key, body, "reminder", appointment.id):
                    sent_keys.add(due)
                    appointment.set_reminder_set(sent_keys)
                    if appointment.status == "pending":
                        appointment.status = "no_response"
                    db.commit()
        patients = list(db.scalars(select(Patient).where(Patient.last_session_at.is_not(None), Patient.opted_out.is_(False))))
        for patient in patients:
            upcoming = db.scalar(select(Appointment.id).where(Appointment.patient_id == patient.id, Appointment.starts_at > now, Appointment.status.not_in(["cancelled", "released", "attended", "no_show"])).limit(1))
            stage = followup_stage(patient.last_session_at, bool(upcoming), now)
            if stage is None:
                patient.followup_status = "normal"
                continue
            patient.followup_status = "risk" if stage >= 14 else "next_session"
            # Per-patient stage key provides idempotency, including across a restart.
            key = f"followup:{patient.id}:{stage}:{patient.last_session_at.date().isoformat()}"
            if not db.scalar(select(MessageLog).where(MessageLog.idempotency_key == key)):
                body = "Hola, queríamos saber si deseas coordinar la próxima visita. Si necesitas ayuda con los horarios, puedes responder a este mensaje. Para dejar de recibir mensajes, responde STOP."
                safe_send(db, whatsapp, patient, key, body, "followup")
        db.commit()
    except Exception:
        db.rollback()
        log.exception("Falló el trabajo programado del panel")
    finally:
        db.close()
