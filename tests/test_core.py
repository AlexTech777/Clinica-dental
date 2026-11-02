import os
import re
from datetime import datetime, timedelta

os.environ.setdefault("SEED_DEMO", "false")
os.environ.setdefault("DRY_RUN", "true")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database
import main
from database import Base
from models import Appointment, Patient, User, WaitlistEntry
from services.parsers import parse_calendar_event, parse_whatsapp_reply
from services.rules import followup_stage, is_waitlist_compatible


def test_calendar_parser_follows_title_and_phone_convention():
    parsed = parse_calendar_event({
        "id": "event-1", "summary": "María Pérez - Endodoncia (2/3)",
        "description": "Tel: +56912345678",
        "start": {"dateTime": "2030-05-10T12:30:00-04:00"},
    })
    assert (parsed["name"], parsed["treatment"]) == ("María Pérez", "Endodoncia")
    assert (parsed["session_number"], parsed["session_total"]) == (2, 3)
    assert parsed["phone"] == "+56912345678"
    assert not parsed["requires_attention"]
    missing = parse_calendar_event({"summary":"Paciente - Control","start":{"date":"2030-05-10"}})
    assert missing["requires_attention"] and missing["phone"] is None


def test_whatsapp_reply_parser_accepts_requested_variants():
    for word in ("1", "sí", "si", "ok", "confirmo"):
        assert parse_whatsapp_reply(word) == "confirm"
    for word in ("2", "no puedo", "cancelar", "reprogramar"):
        assert parse_whatsapp_reply(word) == "reschedule"
    assert parse_whatsapp_reply("STOP") == "stop"


def test_followup_stages_and_waitlist_compatibility():
    now = datetime(2030, 5, 20, 12)
    assert followup_stage(now-timedelta(days=2), False, now) is None
    assert followup_stage(now-timedelta(days=3), False, now) == 3
    assert followup_stage(now-timedelta(days=7), False, now) == 7
    assert followup_stage(now-timedelta(days=14), False, now) == 14
    assert followup_stage(now-timedelta(days=30), True, now) is None
    entry = WaitlistEntry(treatment="Endodoncia", preferred_times="lunes, martes", status="waiting")
    appt = Appointment(treatment="Endodoncia", starts_at=datetime(2030,5,21,10), duration_minutes=60, status="released")
    assert is_waitlist_compatible(entry, appt)
    appt.treatment="Limpieza"
    assert not is_waitlist_compatible(entry, appt)


def test_booking_validation_persistence_and_separate_views(monkeypatch):
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread":False}, poolclass=StaticPool)
    Base.metadata.create_all(test_engine)
    TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(database, "SessionLocal", TestSession)
    monkeypatch.setattr(main, "SessionLocal", TestSession)
    monkeypatch.setattr(main, "engine", test_engine)
    def override_db():
        db=TestSession()
        try: yield db
        finally: db.close()
    main.app.dependency_overrides[database.get_db]=override_db
    monkeypatch.setattr(main, "calendar_service", lambda: type("Calendar", (), {"connected":False})())
    with TestClient(main.app) as client:
        assert client.get("/resumen", follow_redirects=False).status_code == 303
        assert client.get("/health").status_code == 200
        registration_page = client.get("/auth/register")
        assert registration_page.status_code == 200 and "Crear cuenta" in registration_page.text
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', registration_page.text).group(1)
        registration = client.post("/auth/register", data={
            "email": "Recepcion@Ejemplo.com",
            "password": "una-clave-segura-123",
            "password_confirmation": "una-clave-segura-123",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert registration.status_code == 303
        account_db = TestSession()
        account = account_db.query(User).one()
        assert account.email == "recepcion@ejemplo.com"
        assert account.password_hash != "una-clave-segura-123"
        account_db.close()
        assert client.get("/resumen").status_code == 200

        agenda=client.get("/agenda")
        assert agenda.status_code==200 and "Agendar paciente" in agenda.text
        invalid=client.post("/appointments/create",data={"name":"Laura","phone":"123","treatment":"Endodoncia","day":(datetime.now()+timedelta(days=2)).strftime("%Y-%m-%d"),"hour":"12:00","duration":"45"},follow_redirects=True)
        assert "teléfono" in invalid.text.lower()
        future=(datetime.now()+timedelta(days=3)).replace(second=0,microsecond=0)
        response=client.post("/appointments/create",data={"name":"Paciente Demo","phone":"+56912345677","treatment":"Endodoncia","day":future.strftime("%Y-%m-%d"),"hour":"12:30","duration":"60","session_number":"2","session_total":"3"},follow_redirects=True)
        assert response.status_code==200
        assert "Cita guardada" in response.text and "Pendiente" in response.text
        patients=client.get("/pacientes")
        assert "Paciente Demo" in patients.text and "Citas y próximos días" not in patients.text
        wait=client.get("/lista-espera")
        assert wait.status_code==200 and "Personas en espera" in wait.text and "Paciente Demo" not in wait.text
        empty_dashboard = client.get("/resumen")
        assert "No hay citas programadas para mañana." in empty_dashboard.text
        review_patient = Patient(name="Paciente sin contacto", phone=None, treatment="Control")
        db = TestSession()
        confirmed_patient = db.query(Patient).filter(Patient.phone == "+56912345677").one()
        early_tomorrow = datetime.combine(main.now_local().date() + timedelta(days=1), datetime.min.time()).replace(hour=8)
        db.add(Appointment(patient_id=confirmed_patient.id, starts_at=early_tomorrow, duration_minutes=30, treatment="Endodoncia",
            status="pending", sync_state="local"))
        db.add(review_patient)
        db.flush()
        tomorrow = datetime.combine(main.now_local().date() + timedelta(days=1), datetime.min.time()).replace(hour=10)
        db.add(Appointment(patient_id=review_patient.id, starts_at=tomorrow, duration_minutes=30, treatment="Control",
            status="pending", sync_state="pending", attention_required=True))
        db.commit()
        db.close()
        dashboard = client.get("/resumen")
        assert "Deja lista la agenda de mañana" in dashboard.text
        assert "Paciente sin contacto" in dashboard.text
        assert "Revisar contacto" in dashboard.text
        assert "Pendiente en Calendar" in dashboard.text
        assert "Confirmar cita" in dashboard.text
        assert dashboard.text.index("Paciente sin contacto") < dashboard.text.index("Paciente Demo")
        assert f"from_date={tomorrow:%Y-%m-%d}" in dashboard.text

        logout_token = re.search(r'name="csrf_token" value="([^"]+)"', dashboard.text).group(1)
        assert client.post("/auth/logout", data={"csrf_token": logout_token}, follow_redirects=False).status_code == 303
        assert client.get("/resumen", follow_redirects=False).status_code == 303
        registration_page = client.get("/auth/register")
        registration_csrf = re.search(r'name="csrf_token" value="([^"]+)"', registration_page.text).group(1)
        duplicate_account = client.post("/auth/register", data={
            "email": "recepcion@ejemplo.com",
            "password": "una-clave-segura-123",
            "password_confirmation": "una-clave-segura-123",
            "csrf_token": registration_csrf,
        }, follow_redirects=False)
        assert duplicate_account.status_code == 409
        login_page = client.get("/auth/login")
        assert login_page.status_code == 200 and "Iniciar sesión" in login_page.text
        login_csrf = re.search(r'name="csrf_token" value="([^"]+)"', login_page.text).group(1)
        invalid_csrf = client.post("/auth/login", data={
            "email": "recepcion@ejemplo.com",
            "password": "una-clave-segura-123",
            "csrf_token": "invalid",
        })
        assert invalid_csrf.status_code == 400
        invalid_login = client.post("/auth/login", data={
            "email": "recepcion@ejemplo.com",
            "password": "clave-incorrecta",
            "csrf_token": login_csrf,
        })
        assert invalid_login.status_code == 401
        successful_login = client.post("/auth/login", data={
            "email": "recepcion@ejemplo.com",
            "password": "una-clave-segura-123",
            "csrf_token": login_csrf,
        }, follow_redirects=False)
        assert successful_login.status_code == 303
        assert client.get("/resumen").status_code == 200
    db=TestSession()
    appt=db.query(Appointment).filter(Appointment.session_number == 2).one()
    patient=db.query(Patient).filter(Patient.phone == "+56912345677").one()
    assert appt.sync_state=="pending" and appt.session_number==2 and patient.phone=="+56912345677"
    assert not hasattr(patient,"diagnosis") and not hasattr(patient,"clinical_notes")
    db.close(); main.app.dependency_overrides.clear(); Base.metadata.drop_all(test_engine); test_engine.dispose()
