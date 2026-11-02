![Python](https://img.shields.io/badge/python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-MVP-orange)

# 🦷 Sonrisa Clara

Panel administrativo para pequeños consultorios dentales.

Google Calendar continúa siendo la agenda principal y Sonrisa Clara añade gestión operativa, seguimiento de pacientes, lista de espera, recordatorios y preparación de agenda.

> ⚠️ Estado actual: DEMO / MVP
>
> No utilizar con datos reales de pacientes sin configurar previamente autenticación, HTTPS, almacenamiento persistente, copias de seguridad y controles de seguridad adecuados.

---

## Características

- 📅 Integración con Google Calendar
- 👥 Gestión básica de pacientes
- ⏳ Lista de espera
- 💬 Recordatorios mediante WhatsApp
- 📊 Dashboard y resumen diario
- 🔔 Seguimiento de pacientes
- ✅ Confirmación de citas
- 🔄 Sincronización automática de eventos

---

## Capturas de pantalla

### Dashboard

![Dashboard](docs/images/dashboard.png)

### Agenda

![Agenda](docs/images/agenda.png)

### Pacientes

![Pacientes](docs/images/pacientes.png)

---

## Tecnologías

- Python 3.11+
- FastAPI
- Jinja2
- SQLAlchemy
- SQLite
- APScheduler
- Docker
- Google Calendar API
- Twilio WhatsApp

---

## Arquitectura

```text
┌─────────────────┐
│ Navegador       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ FastAPI         │
└────────┬────────┘
         │
 ┌───────┼─────────┐
 ▼       ▼         ▼
SQLite Calendar  WhatsApp
        API      (Twilio)
```

---

## Estructura del Proyecto

```text
project/
│
├── main.py
├── services/
│   ├── calendar_service.py
│   └── whatsapp_service.py
│
├── templates/
├── static/
├── database/
├── tests/
├── specs/
│
├── AGENTS.md
└── README.md
```

---

## Documentación Relacionada

| Documento | Descripción |
|------------|------------|
| `AGENTS.md` | Instrucciones permanentes para agentes IA |
| `specs/agendar-paciente.md` | Flujo de agendamiento |
| `specs/icp-user-persona.md` | Perfil de usuario |
| `specs/preparar-agenda-manana.md` | Revisión diaria de agenda |

---

# 🚀 Inicio Rápido

## Opción 1: Docker (Recomendado)

### Clonar proyecto

```bash
git clone <repositorio>
cd sonrisa-clara
```

### Crear archivo .env

```powershell
Copy-Item .env.example .env
```

### Levantar aplicación

```bash
docker compose up --build
```

### Abrir aplicación

```text
http://localhost:8000
```

La aplicación cargará datos de demostración y no enviará mensajes reales mientras `DRY_RUN=true`.

---

## Opción 2: Entorno Virtual

Crear entorno:

```bash
python -m venv .venv
```

Activar:

```powershell
.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar:

```bash
python main.py
```

Abrir:

```text
http://127.0.0.1:8000
```

---

# Configuración

## Variables de Entorno

| Variable | Descripción |
|-----------|-------------|
| APP_ENV | Entorno de ejecución |
| DRY_RUN | Simulación de mensajes |
| GOOGLE_CALENDAR_ID | ID del calendario |
| GOOGLE_SERVICE_ACCOUNT_FILE | JSON de credenciales |
| SESSION_SECRET_KEY | Clave de sesiones |
| TWILIO_ACCOUNT_SID | Cuenta Twilio |
| TWILIO_AUTH_TOKEN | Token Twilio |
| TWILIO_WHATSAPP_FROM | Número remitente |
| ASSISTANT_WHATSAPP | Número de asistente |

---

# Funcionalidades

## Agenda

Permite:

- Crear citas
- Modificar citas
- Cancelar citas
- Confirmar asistencia
- Actualizar Google Calendar

Si Google Calendar no está configurado, la cita queda marcada como:

```text
Pendiente de sincronización
```

---

## Pacientes

Permite:

- Registrar pacientes
- Agendar nuevas citas
- Gestionar estados de seguimiento
- Detectar riesgos de abandono

Estados disponibles:

- Completado
- Pausado
- Abandonado
- Seguimiento

---

## Lista de Espera

Permite:

- Registrar pacientes interesados
- Gestionar prioridades
- Cubrir cancelaciones automáticamente

---

## Resumen

Incluye:

- Citas pendientes de confirmar
- Pacientes sin teléfono
- Eventos pendientes de sincronización
- Preparación de agenda del día siguiente

---

# Google Calendar

La integración utiliza una cuenta de servicio.

Pasos básicos:

1. Crear proyecto en Google Cloud.
2. Habilitar Google Calendar API.
3. Crear cuenta de servicio.
4. Compartir calendario.
5. Configurar variables de entorno.

Consultar la documentación oficial en:

```text
Google Cloud Console
```

---

# WhatsApp

Integración mediante Twilio.

Funciones:

- Confirmación de citas
- Cancelaciones
- Reprogramaciones
- Seguimientos automáticos

Modo seguro:

```env
DRY_RUN=true
```

En este modo los mensajes no se envían realmente.

---

# Seguridad

## Estado actual

⚠️ La aplicación está pensada actualmente como demostración.

Limitaciones actuales:

- Registro abierto
- Espacio compartido
- SQLite local
- Sin aislamiento por clínica

---

## Recomendaciones para Producción

- HTTPS obligatorio
- Secretos en variables de entorno
- Backups automáticos
- Registro cerrado
- Gestión de usuarios y permisos
- Persistencia de almacenamiento
- Monitorización

---

# Tests

Ejecutar:

```bash
python -m pytest -q
```

Las pruebas cubren:

- Autenticación
- Registro
- Agenda
- Integración Calendar
- WhatsApp
- Validaciones
- Seguimiento

---

# Despliegue

## Docker

Construcción:

```bash
docker build -t usuario/dental-app:latest .
```

Publicación:

```bash
docker push usuario/dental-app:latest
```

---

## Render

Variables mínimas:

```env
APP_ENV=production
DRY_RUN=true
SEED_DEMO=false
SESSION_SECRET_KEY=<clave_segura>
```

Antes de usar pacientes reales:

- Configurar almacenamiento persistente
- Habilitar HTTPS
- Activar copias de seguridad
- Validar integraciones

---

# Limitaciones

Actualmente la aplicación:

- No es un expediente clínico
- No almacena diagnósticos
- No almacena notas médicas
- No gestiona facturación
- No reemplaza sistemas clínicos certificados

---

# Licencia

Definir licencia del proyecto según corresponda.

---

# Autor

Sonrisa Clara - Sistema de gestión para consultorios dentales. - Alexsystems 

Desarrollado por Alexander González.

Proyecto personal de automatización y gestión para consultorios dentales utilizando Python, FastAPI, Docker, Google Calendar y WhatsApp.