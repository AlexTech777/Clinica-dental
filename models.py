import json
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), unique=True, index=True, nullable=True)
    treatment: Mapped[str] = mapped_column(String(100), nullable=False, default="Por confirmar")
    followup_status: Mapped[str] = mapped_column(String(30), nullable=False, default="normal")
    last_contact: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_session_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    opted_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient", cascade="all, delete-orphan")


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=45)
    treatment: Mapped[str] = mapped_column(String(100), nullable=False)
    session_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    calendar_event_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    sync_state: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    sync_error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    attention_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reminder_keys: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    followup_days: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    patient: Mapped[Patient] = relationship(back_populates="appointments")

    def reminder_set(self):
        try: return set(json.loads(self.reminder_keys or "[]"))
        except (ValueError, TypeError): return set()

    def set_reminder_set(self, values): self.reminder_keys = json.dumps(sorted(values))
    def followup_set(self):
        try: return set(json.loads(self.followup_days or "[]"))
        except (ValueError, TypeError): return set()


class WaitlistEntry(Base):
    __tablename__ = "waitlist"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    treatment: Mapped[str] = mapped_column(String(100), nullable=False)
    preferred_times: Mapped[str] = mapped_column(String(180), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="waiting")
    priority: Mapped[str] = mapped_column(String(30), nullable=False, default="Estándar")
    released_appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)


class MessageLog(Base):
    __tablename__ = "message_log"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_message_idempotency"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), nullable=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="sent")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class AppSetting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(String(300), nullable=False)
