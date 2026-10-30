# Guía persistente del proyecto

## Propósito
Este panel ayuda a una asistente de un consultorio dental pequeño a organizar citas, solicitudes y seguimientos. Google Calendar sigue siendo la agenda principal; el panel la complementa.

## Reglas del producto
- Guarda solo nombre, teléfono, tratamiento general, cita y estado de seguimiento. No guardes diagnósticos, notas clínicas, radiografías, síntomas ni expedientes.
- Usa español claro, cálido y profesional. Evita alarmar o culpabilizar a pacientes.
- Haz visibles los límites de integración: demo, pendientes de sincronización, conectada o error.
- Separa las vistas Resumen, Agenda, Pacientes, Lista de espera y Configuración; no mezcles listas de otras secciones.
- Los controles visibles deben funcionar y confirmar éxito/error. Usa estados con texto, no solo color.

## Seguridad y privacidad
- Secretos solo en variables de entorno o archivos locales excluidos de Git; nunca en HTML, logs ni commits.
- Valida entradas y firmas de webhooks; evita mensajes duplicados y respeta STOP en todo envío futuro.
- Mantén `DRY_RUN` disponible por defecto para nuevas instalaciones.
- Usa consultas SQLAlchemy parametrizadas; evita registrar el cuerpo completo de mensajes o datos personales.

## Ingeniería
- Conserva FastAPI, Jinja2, SQLAlchemy/SQLite y servicios intercambiables para Calendar y WhatsApp.
- Revisa `specs/agendar-paciente.md` antes de cambiar el flujo principal.
- Revisa `skills/diseno-de-marca/SKILL.md` al modificar la identidad o interfaz.
- Incluye manejo de error, estados vacíos y accesibilidad de teclado en nuevas pantallas.
- Ejecuta los tests pertinentes si el cambio modifica reglas, persistencia o integraciones.
