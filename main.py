import logging
import os
import re
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import quote

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import secrets

from database import Base, SessionLocal, engine, get_db
from models import AppSetting, Appointment, MessageLog, Patient, WaitlistEntry
from services.calendar_service import GoogleCalendarService
from services.jobs import offer_waitlist, run_automation_jobs, safe_send, within_message_window
from services.parsers import parse_calendar_event, parse_whatsapp_reply
from services.time import now_local
from services.whatsapp_service import WhatsAppService

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("dental_panel")
ROOT = Path(__file__).parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))
templates.env.filters["cldate"] = lambda value: value.strftime("%d/%m/%Y") if value else "—"
templates.env.filters["cltime"] = lambda value: value.strftime("%H:%M") if value else "—"
scheduler = BackgroundScheduler(timezone=os.getenv("TIMEZONE", "America/Santiago"))
calendar_status = {"last_sync": None, "error": None}


def calendar_service():
    return GoogleCalendarService(os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or None,
        os.getenv("GOOGLE_CALENDAR_ID") or None, dry_run=False)


def whatsapp_service(db=None):
    dry = str(get_setting(db, "dry_run", os.getenv("DRY_RUN", "true"))).lower() in {"1", "true", "yes", "on"}
    return WhatsAppService(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"), os.getenv("TWILIO_WHATSAPP_FROM"), dry)


def get_setting(db, key, default):
    if db is None:
        return default
    record = db.get(AppSetting, key)
    return record.value if record else default


def set_setting(db, key, value):
    record = db.get(AppSetting, key)
    if record:
        record.value = str(value)
    else:
        db.add(AppSetting(key=key, value=str(value)))


def normalize_phone(value):
    phone = re.sub(r"[\s()-]", "", value or "")
    if phone.startswith("00"):
        phone = "+" + phone[2:]
    if phone and not phone.startswith("+"):
        phone = "+" + phone
    digits = phone[1:] if phone.startswith("+") else phone
    if not digits.isdigit() or not 8 <= len(digits) <= 15:
        raise ValueError("Ingresa un teléfono con código de país, por ejemplo +56912345678.")
    return phone


def parse_form_datetime(day, hour):
    try:
        value = datetime.combine(date.fromisoformat(day), time.fromisoformat(hour))
    except ValueError as exc:
        raise ValueError("Revisa la fecha y la hora de la cita.") from exc
    if value <= now_local() - timedelta(minutes=1):
        raise ValueError("La fecha y hora deben ser futuras.")
    return value


def flash_redirect(path, message, kind="success"):
    return RedirectResponse(f"{path}?flash={quote(message)}&kind={quote(kind)}", status_code=303)


def appointment_label(status):
    return {"pending": "Pendiente", "confirmed": "Confirmada", "reschedule": "Reprogramar", "no_response": "Sin respuesta", "attended": "Asistió", "no_show": "No asistió", "cancelled": "Cancelada", "released": "Espacio liberado"}.get(status, status)


def page(request, template, db, active, **extra):
    return templates.TemplateResponse(request=request, name=template, context={
        "active": active, "today": date.today(), "calendar": calendar_service(),
        "twilio": whatsapp_service(db), "dry_run": str(get_setting(db, "dry_run", os.getenv("DRY_RUN", "true"))).lower() in {"1", "true", "yes", "on"},
        "message_start": get_setting(db, "message_start", os.getenv("MESSAGE_START_HOUR", "9")),
        "message_end": get_setting(db, "message_end", os.getenv("MESSAGE_END_HOUR", "20")),
        "calendar_status": calendar_status, **extra,
    })


def seed_demo(db):
    if os.getenv("SEED_DEMO", "true").lower() not in {"1", "true", "yes", "on"} or db.scalar(select(func.count(Patient.id))):
        return
    now = now_local().replace(second=0, microsecond=0)
    patients = [
        Patient(name="María Pérez", phone="+56912345678", treatment="Endodoncia", followup_status="normal"),
        Patient(name="Diego Soto", phone="+56987654321", treatment="Ortodoncia", followup_status="next_session", last_session_at=now-timedelta(days=5)),
        Patient(name="Camila Rojas", phone="+56911223344", treatment="Limpieza dental", followup_status="risk", last_session_at=now-timedelta(days=16)),
        Patient(name="Javier Muñoz", phone=None, treatment="Evaluación", followup_status="attention"),
    ]
    db.add_all(patients); db.flush()
    appointments = [
        Appointment(patient_id=patients[0].id, starts_at=now+timedelta(hours=5), duration_minutes=60, treatment="Endodoncia", session_number=2, session_total=3, status="confirmed", sync_state="local"),
        Appointment(patient_id=patients[1].id, starts_at=now+timedelta(days=1, hours=4), duration_minutes=45, treatment="Ortodoncia", session_number=4, session_total=8, status="pending", sync_state="local"),
        Appointment(patient_id=patients[2].id, starts_at=now+timedelta(days=2, hours=2), duration_minutes=45, treatment="Control dental", status="no_response", sync_state="local"),
        Appointment(patient_id=patients[3].id, starts_at=now+timedelta(days=1, hours=6), duration_minutes=30, treatment="Evaluación", status="pending", sync_state="local", attention_required=True),
    ]
    db.add_all(appointments)
    db.add_all([
        WaitlistEntry(name="Sofía Contreras", phone="+56999887766", treatment="Endodoncia", preferred_times="lunes, martes, miércoles, jueves, viernes", priority="Compatible"),
        WaitlistEntry(name="Tomás Silva", phone="+56988776655", treatment="Limpieza dental", preferred_times="lunes, miércoles, viernes", priority="Estándar"),
    ])
    db.commit()


def sync_calendar(db):
    service = calendar_service()
    if not service.connected:
        calendar_status["error"] = "Calendar sin configurar; las citas nuevas se guardan localmente."
        return 0
    try:
        start, end = now_local()-timedelta(days=30), now_local()+timedelta(days=180)
        events = service.list_events(start, end)
        for event in events:
            parsed = parse_calendar_event(event)
            if not parsed["starts_at"]:
                continue
            appt = db.scalar(select(Appointment).where(Appointment.calendar_event_id == event.get("id")))
            if parsed["cancelled"]:
                if appt:
                    newly_released = appt.status != "released"
                    appt.status = "released"
                    if newly_released:
                        offer_waitlist(db, appt, whatsapp_service(db), os.getenv("ASSISTANT_WHATSAPP"))
                continue
            patient = db.scalar(select(Patient).where(Patient.phone == parsed["phone"])) if parsed["phone"] else None
            if not patient:
                patient = Patient(name=parsed["name"], phone=parsed["phone"], treatment=parsed["treatment"], followup_status="attention" if parsed["requires_attention"] else "normal")
                db.add(patient); db.flush()
            else:
                patient.name = parsed["name"]
                patient.treatment = parsed["treatment"]
            if not appt:
                appt = Appointment(patient_id=patient.id, starts_at=parsed["starts_at"], duration_minutes=45,
                    treatment=parsed["treatment"], session_number=parsed["session_number"], session_total=parsed["session_total"],
                    calendar_event_id=parsed["calendar_event_id"], sync_state="synced", attention_required=parsed["requires_attention"])
                db.add(appt)
            else:
                appt.patient_id = patient.id; appt.starts_at = parsed["starts_at"]; appt.treatment = parsed["treatment"]
                appt.session_number = parsed["session_number"]; appt.session_total = parsed["session_total"]
                appt.sync_state = "synced"; appt.attention_required = parsed["requires_attention"]
        db.commit()
        calendar_status.update(last_sync=now_local(), error=None)
        return len(events)
    except Exception as exc:
        db.rollback()
        calendar_status["error"] = f"No se pudo sincronizar Calendar: {type(exc).__name__}. La información local sigue disponible."
        log.exception("Error sincronizando Google Calendar")
        return 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_demo(db)
    finally:
        db.close()
    scheduler.add_job(background_tick, "interval", minutes=5, id="messages", replace_existing=True, max_instances=1)
    scheduler.add_job(background_calendar_sync, "interval", minutes=10, id="calendar", replace_existing=True, max_instances=1)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


def background_tick():
    db = SessionLocal()
    try:
        run_automation_jobs(whatsapp_service(db), get_setting(db, "message_start", os.getenv("MESSAGE_START_HOUR", "9")), get_setting(db, "message_end", os.getenv("MESSAGE_END_HOUR", "20")))
    finally:
        db.close()


def background_calendar_sync():
    db = SessionLocal()
    try: sync_calendar(db)
    finally: db.close()


app = FastAPI(title=os.getenv("APP_NAME", "Sonrisa Clara"), lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


@app.middleware("http")
async def optional_basic_auth(request: Request, call_next):
    username, password = os.getenv("ADMIN_USERNAME"), os.getenv("ADMIN_PASSWORD")
    if username and password and not request.url.path.startswith("/webhooks/"):
        import base64
        header=request.headers.get("authorization", "")
        valid=False
        if header.startswith("Basic "):
            try:
                raw=base64.b64decode(header[6:],validate=True).decode("utf-8")
                user,sep,secret=raw.partition(":")
                valid=bool(sep and secrets.compare_digest(user,username) and secrets.compare_digest(secret,password))
            except (ValueError,UnicodeDecodeError):
                valid=False
        if not valid:
            return PlainTextResponse("Autenticación requerida.",status_code=401,headers={"WWW-Authenticate":"Basic realm=SonrisaClara"})
    return await call_next(request)


@app.get("/", include_in_schema=False)
def root(): return RedirectResponse("/resumen")


@app.get("/resumen", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    today_start = datetime.combine(date.today(), time.min); tomorrow = today_start+timedelta(days=1); next_day = tomorrow+timedelta(days=1)
    today_appointments = list(db.scalars(select(Appointment).where(Appointment.starts_at >= today_start, Appointment.starts_at < tomorrow).order_by(Appointment.starts_at)))
    tomorrow_appointments = list(db.scalars(select(Appointment).where(Appointment.starts_at >= tomorrow, Appointment.starts_at < next_day).order_by(Appointment.starts_at)))
    upcoming = list(db.scalars(select(Appointment).where(Appointment.starts_at >= today_start).order_by(Appointment.starts_at)))
    confirmable = [a for a in upcoming if a.status in {"confirmed", "pending", "no_response", "reschedule"}]
    confirmed_pct = round(100 * sum(a.status == "confirmed" for a in confirmable) / len(confirmable)) if confirmable else 0
    start_week = today_start-timedelta(days=6)
    week = list(db.scalars(select(Appointment).where(Appointment.starts_at >= start_week, Appointment.starts_at < tomorrow)))
    attended = sum(a.status == "attended" for a in week); no_show = sum(a.status == "no_show" for a in week)
    misses_pct = round(no_show*100/max(attended+no_show,1))
    risk_patients = list(db.scalars(select(Patient).where(Patient.followup_status.in_(["risk", "attention"]))))
    released = list(db.scalars(select(Appointment).where(Appointment.status == "released", Appointment.starts_at >= today_start)))
    abandoned = db.scalar(select(func.count(Patient.id)).where(Patient.followup_status == "abandoned")) or 0
    completed = db.scalar(select(func.count(Patient.id)).where(Patient.followup_status == "completed")) or 0
    recovered = db.scalar(select(func.count(WaitlistEntry.id)).where(WaitlistEntry.status == "booked")) or 0
    rescheduled = db.scalar(select(func.count(Appointment.id)).where(Appointment.status == "reschedule")) or 0
    alerts = [a for a in upcoming if a.attention_required or a.status in {"no_response", "reschedule", "released"}]
    return page(request, "dashboard.html", db, "resumen", today_appointments=today_appointments, tomorrow_appointments=tomorrow_appointments,
        confirmed_pct=confirmed_pct, misses_pct=misses_pct, risk_patients=risk_patients, released=released,
        abandoned=abandoned, completed=completed, recovered=recovered, rescheduled=rescheduled, alerts=alerts, appointment_label=appointment_label)


@app.get("/agenda", response_class=HTMLResponse)
def agenda(request: Request, db: Session = Depends(get_db), from_date: str | None = None, to_date: str | None = None, status: str | None = None):
    start_date = date.fromisoformat(from_date) if from_date else date.today()
    end_date = date.fromisoformat(to_date) if to_date else start_date+timedelta(days=7)
    query = select(Appointment).where(Appointment.starts_at >= datetime.combine(start_date,time.min), Appointment.starts_at < datetime.combine(end_date+timedelta(days=1),time.min)).order_by(Appointment.starts_at)
    if status:
        query = query.where(Appointment.status == status)
    return page(request, "agenda.html", db, "agenda", appointments=list(db.scalars(query)), appointment_label=appointment_label,
        from_date=start_date.isoformat(), to_date=end_date.isoformat(), filter_status=status or "")


@app.post("/appointments/create")
def create_appointment(request: Request, name: str = Form(...), phone: str = Form(...), treatment: str = Form(...), day: str = Form(...), hour: str = Form(...), duration: int = Form(...), session_number: str = Form(""), session_total: str = Form(""), db: Session = Depends(get_db)):
    try:
        if len(name.strip()) < 2 or len(name) > 120: raise ValueError("Escribe el nombre del paciente (máximo 120 caracteres).")
        if not treatment.strip() or len(treatment) > 100: raise ValueError("Escribe un tratamiento general (máximo 100 caracteres).")
        phone = normalize_phone(phone)
        starts_at = parse_form_datetime(day, hour)
        if duration not in {15, 30, 45, 60, 75, 90, 120}: raise ValueError("Selecciona una duración válida entre 15 y 120 minutos.")
        session_n = int(session_number) if session_number else None; session_t = int(session_total) if session_total else None
        if (session_n is None) != (session_t is None) or (session_n is not None and not 1 <= session_n <= session_t):
            raise ValueError("Indica las dos sesiones (actual y total), y asegúrate de que la actual no supere el total.")
        end_at = starts_at + timedelta(minutes=duration)
        overlaps = any(a.starts_at < end_at and a.starts_at+timedelta(minutes=a.duration_minutes) > starts_at
            for a in db.scalars(select(Appointment).where(Appointment.starts_at < end_at, Appointment.status.not_in(["cancelled", "released", "no_show"]))))
        if overlaps: raise ValueError("Ese horario se cruza con otra cita. Elige un espacio distinto.")
        patient = db.scalar(select(Patient).where(Patient.phone == phone))
        if not patient:
            patient = Patient(name=name.strip(), phone=phone, treatment=treatment.strip())
            db.add(patient); db.flush()
        else:
            patient.name = name.strip(); patient.treatment = treatment.strip()
        appt = Appointment(patient_id=patient.id, starts_at=starts_at, duration_minutes=duration, treatment=treatment.strip(),
            session_number=session_n, session_total=session_t, status="pending", sync_state="pending")
        db.add(appt); db.commit(); db.refresh(appt)
        try:
            service = calendar_service()
            if service.connected:
                appt.calendar_event_id = service.create_event(appt, patient); appt.sync_state = "synced"; appt.sync_error = None
            else:
                appt.sync_state = "pending"; appt.sync_error = "Google Calendar no está configurado."
            db.commit()
        except Exception as exc:
            db.rollback()
            appt = db.get(Appointment, appt.id); appt.sync_state = "pending"; appt.sync_error = f"Error Calendar: {type(exc).__name__}. Reintenta desde Configuración."; db.commit()
            calendar_status["error"] = appt.sync_error
        return flash_redirect("/agenda", f"Cita guardada. Estado de Calendar: {appt.sync_state.replace('_',' ')}.")
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        reason = str(exc) if isinstance(exc, ValueError) else "No se pudo guardar la cita. Verifica si el teléfono ya está asociado a otro registro."
        return flash_redirect("/agenda", reason, "error")


@app.post("/appointments/{appointment_id}/edit")
def edit_appointment(appointment_id: int, day: str = Form(...), hour: str = Form(...), duration: int = Form(...), db: Session = Depends(get_db)):
    appt = db.get(Appointment, appointment_id)
    if not appt: raise HTTPException(404, "Cita no encontrada")
    try:
        new_start = parse_form_datetime(day,hour)
        if duration not in {15,30,45,60,75,90,120}: raise ValueError("Duración no válida.")
        end_at=new_start+timedelta(minutes=duration)
        overlaps=any(other.id!=appt.id and other.starts_at<end_at and other.starts_at+timedelta(minutes=other.duration_minutes)>new_start
            for other in db.scalars(select(Appointment).where(Appointment.starts_at<end_at,Appointment.status.not_in(["cancelled","released","no_show"]))))
        if overlaps: raise ValueError("Ese horario se cruza con otra cita.")
        appt.starts_at = new_start
        appt.duration_minutes = duration
        service = calendar_service()
        if service.connected:
            appt.calendar_event_id=service.update_event(appt,appt.patient); appt.sync_state="synced"; appt.sync_error=None
        else:
            appt.sync_state="pending"; appt.sync_error="Pendiente de actualizar en Google Calendar."
        db.commit()
        return flash_redirect("/agenda", "Cambios guardados localmente. Sincroniza el evento desde Calendar si está conectado.")
    except ValueError as exc:
        db.rollback(); return flash_redirect("/agenda", str(exc), "error")


@app.post("/appointments/{appointment_id}/status")
def set_appointment_status(appointment_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    allowed = {"confirmed", "reschedule", "attended", "no_show", "cancelled", "released", "pending"}
    appt = db.get(Appointment, appointment_id)
    if not appt: raise HTTPException(404, "Cita no encontrada")
    if status not in allowed: raise HTTPException(400, "Estado no válido")
    appt.status = status
    if status in {"cancelled", "released", "reschedule"}:
        appt.status = "released"
        try:
            calendar_service().cancel_event(appt.calendar_event_id)
            appt.calendar_event_id = None; appt.sync_state = "synced"; appt.sync_error = None
        except Exception as exc:
            appt.sync_state = "pending"; appt.sync_error = f"Pendiente de cancelar en Calendar: {type(exc).__name__}."
        db.commit()
        offer_waitlist(db, appt, whatsapp_service(db), os.getenv("ASSISTANT_WHATSAPP"))
    elif status in {"attended", "no_show"}:
        if status == "attended":
            appt.patient.last_session_at = appt.starts_at
            appt.patient.followup_status = "completed" if appt.session_number and appt.session_total and appt.session_number >= appt.session_total else "normal"
        else:
            if not appt.patient.opted_out:
                safe_send(db, whatsapp_service(db), appt.patient, f"noshow:{appt.id}", "Hola, sentimos que no hayas podido asistir. Si deseas, podemos ayudarte a encontrar otro horario. Responde a este mensaje para coordinarlo; para no recibir más mensajes, responde STOP.", "no_show", appt.id)
            appt.status = "no_show"
        db.commit()
    else:
        db.commit()
    return flash_redirect("/agenda", "Estado de la cita actualizado.")


@app.post("/appointments/{appointment_id}/remind")
def remind(appointment_id: int, db: Session = Depends(get_db)):
    appt = db.get(Appointment, appointment_id)
    if not appt: raise HTTPException(404)
    now = now_local()
    start_hour = int(get_setting(db,"message_start",os.getenv("MESSAGE_START_HOUR","9")))
    end_hour = int(get_setting(db,"message_end",os.getenv("MESSAGE_END_HOUR","20")))
    if not within_message_window(now,start_hour,end_hour): return flash_redirect("/agenda", f"Los mensajes están permitidos de {start_hour:02d}:00 a {end_hour:02d}:00.","error")
    sent = safe_send(db, whatsapp_service(db), appt.patient, f"appointment:{appt.id}:manual:{now:%Y%m%d%H%M}", f"Hola, te recordamos tu cita dental el {appt.starts_at:%d/%m a las %H:%M}. Responde 1 para confirmar o 2 si necesitas reprogramar. Responde STOP para dejar de recibir mensajes.", "reminder", appt.id)
    return flash_redirect("/agenda", "Recordatorio enviado." if sent else "No se envió: revisa el modo DRY_RUN, el teléfono o la baja de mensajes.", "success" if sent else "error")


@app.get("/pacientes", response_class=HTMLResponse)
def patients(request: Request, db: Session = Depends(get_db)):
    records = list(db.scalars(select(Patient).order_by(Patient.name)))
    now = now_local()
    items = []
    for patient in records:
        next_appointment = db.scalar(select(Appointment).where(Appointment.patient_id == patient.id, Appointment.starts_at > now, Appointment.status.not_in(["cancelled","released","no_show","attended"])).order_by(Appointment.starts_at).limit(1))
        attended = list(db.scalars(select(Appointment).where(Appointment.patient_id == patient.id, Appointment.status == "attended").order_by(Appointment.starts_at.desc())))
        progress = "Sin cita" if not next_appointment else (f"Sesión {next_appointment.session_number}/{next_appointment.session_total}" if next_appointment.session_number and next_appointment.session_total else "En seguimiento")
        if patient.followup_status == "abandoned": category="Tratamiento abandonado"
        elif patient.followup_status in {"risk","attention"}: category="Riesgo de abandono" if patient.followup_status == "risk" else "Requiere atención"
        elif next_appointment is None and patient.last_session_at: category="Próxima sesión pendiente"
        else: category="En seguimiento normal"
        items.append({"patient":patient,"next":next_appointment,"last":attended[0].starts_at if attended else patient.last_contact,"progress":progress,"category":category})
    return page(request,"patients.html",db,"pacientes",items=items)


@app.post("/patients/{patient_id}/followup")
def patient_followup(patient_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    if status not in {"normal","next_session","risk","abandoned","paused","completed","attention"}: raise HTTPException(400)
    patient = db.get(Patient, patient_id)
    if not patient: raise HTTPException(404)
    patient.followup_status = status; db.commit()
    return flash_redirect("/pacientes","Estado de seguimiento actualizado.")


@app.post("/patients/{patient_id}/contact")
def patient_contact(patient_id:int, db:Session=Depends(get_db)):
    patient=db.get(Patient,patient_id)
    if not patient: raise HTTPException(404)
    start=int(get_setting(db,"message_start",os.getenv("MESSAGE_START_HOUR","9"))); end=int(get_setting(db,"message_end",os.getenv("MESSAGE_END_HOUR","20")))
    now=now_local()
    if not within_message_window(now,start,end): return flash_redirect("/pacientes",f"Los mensajes están permitidos de {start:02d}:00 a {end:02d}:00.","error")
    sent=safe_send(db,whatsapp_service(db),patient,f"contact:{patient.id}:{now:%Y%m%d%H%M}","Hola, te saluda el consultorio dental. ¿En qué podemos ayudarte con tu próxima visita? Responde STOP para dejar de recibir mensajes.","manual")
    return flash_redirect("/pacientes","Mensaje enviado." if sent else "No se envió: revisa el teléfono, DRY_RUN o la baja de mensajes.","success" if sent else "error")


@app.get("/lista-espera", response_class=HTMLResponse)
def waitlist(request: Request, db:Session=Depends(get_db)):
    rows=list(db.scalars(select(WaitlistEntry).order_by(WaitlistEntry.created_at,WaitlistEntry.id)))
    return page(request,"waitlist.html",db,"espera",entries=rows)


@app.post("/waitlist/create")
def create_waitlist(name:str=Form(...),phone:str=Form(...),treatment:str=Form(...),preferred_times:str=Form(""),db:Session=Depends(get_db)):
    try:
        if not name.strip() or not treatment.strip(): raise ValueError("Nombre y tratamiento son obligatorios.")
        norm=normalize_phone(phone)
        db.add(WaitlistEntry(name=name.strip(),phone=norm,treatment=treatment.strip(),preferred_times=preferred_times[:180])); db.commit()
        return flash_redirect("/lista-espera","Paciente agregado a la lista de espera.")
    except ValueError as exc:
        db.rollback(); return flash_redirect("/lista-espera",str(exc),"error")


@app.post("/waitlist/{entry_id}/status")
def update_waitlist(entry_id:int,status:str=Form(...),db:Session=Depends(get_db)):
    if status not in {"waiting","contacted","accepted","rejected","booked"}: raise HTTPException(400)
    entry=db.get(WaitlistEntry,entry_id)
    if not entry: raise HTTPException(404)
    if status=="contacted" and entry.status=="waiting":
        start=int(get_setting(db,"message_start",os.getenv("MESSAGE_START_HOUR","9"))); end=int(get_setting(db,"message_end",os.getenv("MESSAGE_END_HOUR","20")))
        if not within_message_window(now_local(),start,end): return flash_redirect("/lista-espera",f"Los mensajes están permitidos de {start:02d}:00 a {end:02d}:00.","error")
        key=f"waitlist:manual:{entry.id}"
        existing=db.scalar(select(MessageLog).where(MessageLog.idempotency_key==key))
        if not existing:
            record=MessageLog(idempotency_key=key,category="waitlist",status="sending")
            db.add(record); entry.status="contacted"; db.commit()
            try:
                result=whatsapp_service(db).send(entry.phone,"Hola, recibimos tu solicitud para la lista de espera del consultorio. Te contactaremos si aparece un horario compatible. Responde STOP si prefieres dejar de recibir mensajes.",key)
                record.provider_id=result.get("sid"); record.status="dry_run" if result.get("dry_run") else "sent"; db.commit()
            except Exception as exc:
                record.status="failed"; db.commit()
                return flash_redirect("/lista-espera",f"No se pudo enviar el mensaje ({type(exc).__name__}). Puedes reintentar más tarde.","error")
        else:
            entry.status="contacted"; db.commit()
        return flash_redirect("/lista-espera","Solicitud marcada como contactada.")
    entry.status=status; db.commit()
    return flash_redirect("/lista-espera","Estado de la lista actualizado.")


@app.get("/configuracion", response_class=HTMLResponse)
def settings_page(request:Request,db:Session=Depends(get_db)):
    return page(request,"settings.html",db,"configuracion",service_calendar=calendar_service(),service_whatsapp=whatsapp_service(db))


@app.post("/configuracion")
def save_settings(message_start:int=Form(...),message_end:int=Form(...),dry_run:str=Form("false"),db:Session=Depends(get_db)):
    if not 0 <= message_start < message_end <= 24: return flash_redirect("/configuracion","El horario debe ser válido y cubrir más de una hora.","error")
    set_setting(db,"message_start",message_start); set_setting(db,"message_end",message_end); set_setting(db,"dry_run",dry_run.lower() in {"true","on","1"}); db.commit()
    return flash_redirect("/configuracion","Configuración guardada.")


@app.post("/configuracion/sincronizar")
def manual_sync(db:Session=Depends(get_db)):
    n=sync_calendar(db)
    return flash_redirect("/configuracion",f"Sincronización completada: {n} eventos revisados." if not calendar_status["error"] else calendar_status["error"],"success" if not calendar_status["error"] else "error")


@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request:Request,db:Session=Depends(get_db)):
    form=await request.form(); params=dict(form); signature=request.headers.get("X-Twilio-Signature","")
    token=os.getenv("TWILIO_AUTH_TOKEN"); webhook_url=os.getenv("TWILIO_WEBHOOK_URL") or str(request.url)
    if not token or not signature or not WhatsAppService.validate_request(token,signature,webhook_url,params):
        raise HTTPException(403,"Firma de Twilio inválida")
    sid=str(params.get("MessageSid", "")); phone=normalize_webhook_phone(str(params.get("From", "")))
    body=str(params.get("Body", "")); action=parse_whatsapp_reply(body)
    if sid and db.scalar(select(MessageLog.id).where(MessageLog.idempotency_key == f"inbound:{sid}")):
        return Response("<Response></Response>",media_type="application/xml")
    patient=db.scalar(select(Patient).where(Patient.phone==phone))
    if action=="stop":
        if patient: patient.opted_out=True; patient.last_contact=now_local()
        for wait_entry in db.scalars(select(WaitlistEntry).where(WaitlistEntry.phone==phone,WaitlistEntry.status.in_(["waiting","contacted"]))):
            wait_entry.status="opted_out"
        logrow=MessageLog(idempotency_key=f"inbound:{sid or now_local().timestamp()}",patient_id=patient.id if patient else None,category="opt_out",status="received")
        db.add(logrow); db.commit()
        return Response("<Response><Message>Listo, dejamos de enviarte recordatorios del consultorio.</Message></Response>",media_type="application/xml")
    entry=db.scalar(select(WaitlistEntry).where(WaitlistEntry.phone==phone,WaitlistEntry.status=="contacted").order_by(WaitlistEntry.created_at).limit(1))
    service=whatsapp_service(db)
    if entry and action in {"confirm","reschedule"}:
        entry.status="accepted" if action=="confirm" else "rejected"
        db.add(MessageLog(idempotency_key=f"inbound:{sid or now_local().timestamp()}",patient_id=patient.id if patient else None,category="waitlist_reply",status="received"))
        db.commit()
        if action=="confirm":
            if os.getenv("ASSISTANT_WHATSAPP"):
                service.send(os.getenv("ASSISTANT_WHATSAPP"),f"{entry.name} aceptó el espacio. Confirma y registra la cita en Google Calendar.",f"assistant-accepted:{entry.id}")
            service.send(phone,"Gracias, avisamos al consultorio para confirmar tu horario.",f"waitlist-accepted:{entry.id}")
        else:
            service.send(phone,"Gracias por avisarnos. Dejamos el horario disponible para otra persona.",f"waitlist-rejected:{entry.id}")
            appt=db.get(Appointment,entry.released_appointment_id) if entry.released_appointment_id else None
            if appt: offer_waitlist(db,appt,service,os.getenv("ASSISTANT_WHATSAPP"))
        return Response("<Response></Response>",media_type="application/xml")
    appointment=None
    if patient:
        appointment=db.scalar(select(Appointment).where(Appointment.patient_id==patient.id,Appointment.starts_at>now_local(),Appointment.status.in_(["pending","confirmed","no_response","reschedule"])).order_by(Appointment.starts_at).limit(1))
    if appointment and action in {"confirm","reschedule"}:
        db.add(MessageLog(idempotency_key=f"inbound:{sid or now_local().timestamp()}",patient_id=patient.id,appointment_id=appointment.id,category="appointment_reply",status="received"))
        if action=="confirm":
            appointment.status="confirmed"; patient.last_contact=now_local(); db.commit(); service.send(phone,"Gracias, tu cita quedó confirmada.",f"confirmation:{sid or appointment.id}")
        else:
            appointment.status="released"; patient.last_contact=now_local()
            try: calendar_service().cancel_event(appointment.calendar_event_id); appointment.calendar_event_id=None; appointment.sync_state="synced"
            except Exception: appointment.sync_state="pending"
            db.commit(); offer_waitlist(db,appointment,service,os.getenv("ASSISTANT_WHATSAPP")); service.send(phone,"Gracias por avisarnos. El consultorio te contactará para coordinar otro horario.",f"reschedule:{sid or appointment.id}")
    elif sid:
        db.add(MessageLog(idempotency_key=f"inbound:{sid}",patient_id=patient.id if patient else None,category="unknown_reply",status="received")); db.commit()
    return Response("<Response></Response>",media_type="application/xml")


def normalize_webhook_phone(value):
    value=value.removeprefix("whatsapp:")
    try: return normalize_phone(value)
    except ValueError: return value[:30]


@app.get("/health")
def health(): return {"status":"ok","app":"sonrisa-clara"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")), reload=False)
