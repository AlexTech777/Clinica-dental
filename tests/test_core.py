import os
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
from models import Appointment, Patient, WaitlistEntry
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
    db=TestSession()
    appt=db.query(Appointment).one(); patient=db.query(Patient).one()
    assert appt.sync_state=="pending" and appt.session_number==2 and patient.phone=="+56912345677"
    assert not hasattr(patient,"diagnosis") and not hasattr(patient,"clinical_notes")
    db.close(); main.app.dependency_overrides.clear(); Base.metadata.drop_all(test_engine); test_engine.dispose()
