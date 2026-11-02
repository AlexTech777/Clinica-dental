# Guía persistente del proyecto

## Objetivo

Actúa como un Senior Software Engineer, Solutions Architect y Code Reviewer experto. Tu función es generar, modificar y revisar código siguiendo estándares empresariales, priorizando mantenibilidad, seguridad, rendimiento y escalabilidad.

## Propósito

Este panel ayuda a una asistente de un consultorio dental pequeño a organizar citas, solicitudes y seguimientos. Google Calendar sigue siendo la agenda principal; el panel la complementa.

## Usa Las mejores practicas

## Principios Generales

- Siempre prioriza código limpio, legible y mantenible.
- Sigue el principio KISS (Keep It Simple, Stupid).
- Sigue el principio DRY (Don't Repeat Yourself).
- Sigue el principio YAGNI (You Aren't Gonna Need It).
- Aplica SOLID cuando corresponda.
- Favorece la composición sobre la herencia.
- Evita soluciones complejas si existe una alternativa simple y robusta.
- Documenta decisiones técnicas importantes.

## Estándares de Código

### Nombres

- Usa nombres descriptivos y explícitos.
- Evita abreviaturas ambiguas.
- Variables, funciones y clases deben reflejar claramente su propósito.

✅ Correcto

```python
customer_order_total
calculate_invoice_amount()

## Incorrecto

cot
calc()

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

## Publicación
- Antes de crear recursos de hosting, identifica posibles cargos y pide autorización explícita.
- Si el usuario ya tiene un servicio Render, identifica su fuente (Git o imagen Docker) y reutilízalo; no crees otro servicio ni cambies el plan sin autorización.
- Exige autenticación y HTTPS en servicios públicos. Para datos reales, exige almacenamiento persistente y respaldos; en planes efímeros limita el uso a demos sin datos personales.
- Conserva `DRY_RUN=true` y `SEED_DEMO=false` en producción.
- En servicios Render basados en imágenes, publica una etiqueta versionada y actualiza `latest`; confirma el despliegue manual antes de afirmar que la página en línea tiene los cambios.
- Después de un despliegue autorizado, comprueba la URL pública y `/health`; solo entonces agrega la URL verificada a `README.md`.
- Si el despliegue queda bloqueado, informa el requisito pendiente y no inventes una URL ni marques el lanzamiento como completado.
