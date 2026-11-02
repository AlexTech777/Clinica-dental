# Sonrisa Clara · Panel de consultorio dental

Panel administrativo para una consulta dental pequeña. Google Calendar continúa como agenda principal; este sistema añade un resumen, directorio mínimo de pacientes, cola de espera y seguimiento. No es un expediente clínico ni guarda diagnósticos.

## Arquitectura

- Python 3.11+, FastAPI, Jinja2, SQLAlchemy/SQLite y APScheduler.
- Pantallas separadas: Resumen, Agenda, Pacientes, Lista de espera y Configuración.
- El feature principal está descrito en [`specs/agendar-paciente.md`](specs/agendar-paciente.md); las instrucciones persistentes están en [`AGENTS.md`](AGENTS.md).
- El perfil de usuario y la nueva revisión de jornada están descritos en [`specs/icp-user-persona.md`](specs/icp-user-persona.md) y [`specs/preparar-agenda-manana.md`](specs/preparar-agenda-manana.md).
- El adaptador `services/whatsapp_service.py` aísla Twilio para poder sustituirlo por Meta Cloud API.
- El adaptador `services/calendar_service.py` lee, crea, actualiza y cancela eventos de Google Calendar. Los IDs de evento son estables para evitar duplicados.
- La interfaz usa Jinja2 y CSS/JavaScript simple, sin framework frontend.

## Inicio en aproximadamente dos minutos

1. Instala Docker Desktop y abre una terminal en esta carpeta.
2. Copia `.env.example` a `.env` (en Windows PowerShell: `Copy-Item .env.example .env`). El modo de demostración y `DRY_RUN` quedan habilitados por defecto.
3. Inicia el panel con una sola orden:

   ```bash
   docker compose up --build
   ```

4. Abre [http://localhost:8000](http://localhost:8000). El panel carga citas y pacientes de demostración; no se envían mensajes reales.

Para correr sin Docker: crea un entorno virtual (`python -m venv .venv`), actívalo, instala `pip install -r requirements.txt` y ejecuta `python main.py`. El panel queda en `http://127.0.0.1:8000`.

Los datos SQLite de Docker viven en un volumen persistente llamado `dental-data`. Para probar otra vez desde cero, detén el servicio y elimina ese volumen **solo si deseas borrar todos los datos de demostración y operación**.

## Usar la Agenda y agendar

Entra en **Agenda**, usa filtros por fecha/estado y selecciona **Agendar paciente**. Nombre, teléfono, tratamiento general, fecha, hora y duración son obligatorios; sesión actual/total es opcional, pero se deben completar ambos. Si la conexión de Calendar no está configurada, el panel guarda la cita en SQLite y muestra “Pendiente de sincronización”. Si Calendar está conectado, crea el evento y conserva su ID. No agendes dos citas que se crucen en el horario.

Editar cambia hora/duración y actualiza Google Calendar si está conectado. Las acciones “Asistió” y “No asistió” actualizan el estado. La inasistencia activa un mensaje de reprogramación. Al cancelar o reprogramar se libera el espacio y se contacta a la primera persona compatible en espera. La asistente confirma la cita en Calendar después de recibir un “SÍ”.

En **Pacientes**, usa Contactar o Agendar y cambia manualmente el seguimiento a completado, pausado, abandonado u otro estado. Se marca riesgo cuando faltan 14 días para la próxima sesión y se envían mensajes de seguimiento programados a los 3, 7 y 14 días cuando no hay una próxima cita.

En **Lista de espera**, registra nombre, teléfono, tratamiento general y preferencia de días. La cola se ordena por antigüedad; se comprueba compatibilidad por tratamiento y día preferido.

En **Resumen**, la sección **Deja lista la agenda de mañana** reúne las citas que requieren confirmación, revisión de contacto o sincronización. El listado prioriza los datos de contacto faltantes y enlaza con la Agenda ya filtrada para ese día; no envía mensajes ni modifica citas.

## Google Calendar

La implementación usa cuenta de servicio, adecuada para un calendario de equipo compartido. Para un calendario personal sin posibilidad de compartir o para cuentas fuera de Google Workspace, configura OAuth en lugar de exponer una llave de servicio.

1. En Google Cloud crea un proyecto y habilita Google Calendar API.
2. Crea una cuenta de servicio, descarga su JSON de credenciales y guarda el archivo fuera del repositorio (está excluido de Git).
3. Comparte el calendario que usa la consulta con el correo de la cuenta de servicio y permiso para hacer cambios en eventos. Copia el ID del calendario desde sus ajustes.
4. En `.env`, define `GOOGLE_CALENDAR_ID` y `GOOGLE_SERVICE_ACCOUNT_FILE` con rutas legibles por el proceso.
5. Pulsa **Sincronizar ahora** en Configuración o espera la sincronización automática cada 10 minutos.

Los títulos se leen como `Nombre Paciente - Tratamiento (X/Y)` y el teléfono como `Tel: +56912345678` en la descripción. Si el título no lleva sesión, es una cita simple. Si falta teléfono, aparece “Requiere atención” y no se envía recordatorio automático. Los eventos cancelados liberan el horario.

Si usas Docker, monta el JSON de forma de solo lectura en el contenedor y apunta `GOOGLE_SERVICE_ACCOUNT_FILE` a esa ruta. No agregues la llave al repositorio ni a una imagen publicada.

## Twilio WhatsApp Sandbox y producción

1. Crea o usa una cuenta de Twilio y activa **Try WhatsApp / Sandbox**. Desde el teléfono de prueba, sigue las instrucciones de conexión del Sandbox.
2. Copia `TWILIO_ACCOUNT_SID` y `TWILIO_AUTH_TOKEN` a `.env`; configura `TWILIO_WHATSAPP_FROM` con el remitente que indique el Sandbox.
3. Para webhooks locales, publica el puerto del servidor con un túnel HTTPS de desarrollo y configura la URL `/webhooks/whatsapp` en “When a Message Comes In” del Sandbox. Define esa URL completa en `TWILIO_WEBHOOK_URL` para validar la firma.
4. Prueba primero con `DRY_RUN=true`. Los mensajes salen en la consola. En Configuración también se puede activar/desactivar el modo.
5. Para enviar de verdad, cambia `DRY_RUN=false`, define el horario permitido y configura `ASSISTANT_WHATSAPP` en formato internacional para los avisos a la asistente.

Los recordatorios están previstos 48 y 3 horas antes, solo entre las 09:00 y 20:00 por defecto. El webhook entiende `1`, “sí”, “si”, “ok”, “confirmo”, `2`, “no puedo”, “cancelar”, “reprogramar” y `STOP`. Los IDs entrantes y las claves de recordatorio se registran para evitar procesar dos veces el mismo evento. Los envíos de empresa en producción pueden necesitar plantillas aprobadas por WhatsApp; el Sandbox usa solo sus plantillas disponibles y la sesión de atención tiene una ventana limitada.

## Temas y preferencias

En **Configuración** elige Grafito y acero, Verde profundo o Azul petróleo. El tema se aplica inmediatamente y se guarda en el navegador. El horario permitido y DRY_RUN se guardan en SQLite.

## Seguridad y datos

- Este demo no trae acceso público multiusuario ni despliegue TLS incluido. En `.env` configura `ADMIN_USERNAME` y una contraseña larga `ADMIN_PASSWORD` para activar autenticación básica, y publica el servicio solo detrás de HTTPS. No expongas una instancia abierta a Internet.
- El webhook de Twilio rechaza solicitudes sin firma válida.
- No se guarda el texto de mensajes, diagnóstico ni notas clínicas. SQLite sí contiene nombres, teléfonos, tratamiento general, citas y estados operativos. Protege el equipo/volumen con controles del sistema operativo y copias de seguridad seguras.
- `STOP` evita todos los envíos futuros a ese teléfono, incluso si está en la lista de espera.
- La aplicación no ofrece facturación ni atención clínica.

## Tests

```bash
python -m pytest -q
```

Cubren el parser de Calendar y de respuestas de WhatsApp, reglas de seguimiento y compatibilidad de espera, validación/guardado de citas y separación de listas por pantalla.

## Configuración de publicación

Antes de alojar el panel para un consultorio real, configura HTTPS, autenticación, respaldos, una cuenta de servicio con acceso limitado al calendario correcto y las plantillas aprobadas de WhatsApp. Conserva `DRY_RUN=true` hasta verificar ambos conectores.

### Publicación en Render

El servicio existente `dental-app:latest` usa la imagen pública `docker.io/alextech777/dental-app:latest`. Render no despliega automáticamente nuevas imágenes del registro; se deben publicar en Docker Hub y activar **Manual Deploy** en el servicio existente. La versión con la revisión de agenda está publicada con la etiqueta `2026-11-02-agenda-manana` y también como `latest`.

Para construir y publicar otra versión desde la raíz del repositorio en Windows PowerShell, usa una etiqueta nueva y luego actualiza `latest`:

```powershell
docker build -t alextech777/dental-app:2026-11-02-agenda-manana .
docker push alextech777/dental-app:2026-11-02-agenda-manana
docker tag alextech777/dental-app:2026-11-02-agenda-manana alextech777/dental-app:latest
docker push alextech777/dental-app:latest
```

En Render, abre el servicio existente y agrega en **Environment** `APP_ENV=production`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `DRY_RUN=true` y `SEED_DEMO=false`. Define el usuario y la contraseña allí; no los incluyas en el código ni en Git. Después abre **Manual Deploy** y despliega la última imagen. El middleware exige las credenciales antes de mostrar las pantallas cuando `APP_ENV=production`; `/health` permanece público y los webhooks conservan su validación de firma.

Al finalizar, verifica `/health`, inicia sesión en la URL existente del servicio y confirma que aparece **Deja lista la agenda de mañana**. Conserva `DRY_RUN=true`. El plan gratuito de Render no ofrece disco persistente: usa esta instancia solo como demo y no guardes datos reales de pacientes. Antes de usar datos reales, configura almacenamiento persistente, respaldos y los controles operativos correspondientes.

Iniciar - Aplicación local

.\.venv\Scripts\Activate.ps1

python main.py

Con Docker:

docker compose up --build