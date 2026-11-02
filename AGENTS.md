# Guía del agente del proyecto

## Propósito

Este panel ayuda a una asistente de un consultorio dental pequeño a organizar citas, solicitudes y seguimientos. Google Calendar sigue siendo la agenda principal; el panel la complementa.

## Principios de ingeniería

- Prioriza soluciones simples, claras, seguras y mantenibles. Evita abstracciones, dependencias y cambios fuera del alcance que no sean necesarios.
- Sigue los patrones existentes del proyecto y conserva su arquitectura: FastAPI, Jinja2, SQLAlchemy/SQLite, CSS y JavaScript; Calendar y WhatsApp se integran mediante servicios intercambiables.
- Lee el código y las pruebas relacionadas antes de cambiar comportamiento. No sobrescribas cambios ajenos al pedido.
- Maneja errores esperados de forma explícita y comprensible. No ocultes fallos con valores de éxito ni captures excepciones de forma general sin registrarlas.
- Conserva el tipado y la validación de entradas. Usa consultas SQLAlchemy parametrizadas.
- Añade o actualiza pruebas cuando cambien reglas, persistencia, autenticación o integraciones; ejecuta las pruebas pertinentes antes de terminar.
- Actualiza la documentación directamente relacionada con el cambio.
- Comenta solo decisiones o comportamientos que no sean evidentes por el código.

## Reglas del producto

- Guarda solo nombre, teléfono, tratamiento general, cita y estado de seguimiento. No guardes diagnósticos, notas clínicas, radiografías, síntomas ni expedientes.
- Usa español claro, cálido y profesional. Evita alarmar o culpabilizar a pacientes.
- Haz visibles los estados de integración: demostración, pendiente de sincronización, conectada o error.
- Mantén separadas las vistas Resumen, Agenda, Pacientes, Lista de espera y Configuración; no mezcles sus listas.
- Todo control visible debe funcionar e informar el resultado. Incluye estados vacíos, etiquetas accesibles y navegación por teclado.
- Revisa `specs/agendar-paciente.md` antes de cambiar el flujo principal y `skills/diseno-de-marca/SKILL.md` al modificar la identidad o la interfaz.

## Seguridad y privacidad

- Guarda secretos solo en variables de entorno o archivos locales excluidos de Git. Nunca los incluyas en HTML, logs, imágenes Docker o commits.
- No registres cuerpos completos de mensajes ni datos personales de pacientes.
- Valida las entradas y firmas de webhooks, evita procesar mensajes duplicados y respeta `STOP` en todos los envíos futuros.
- Mantén `DRY_RUN=true` como valor predeterminado para nuevas instalaciones y pruebas.
- El panel permite crear cuentas y actualmente las cuentas comparten los mismos pacientes, citas y datos del consultorio. Mientras el registro esté abierto, cualquiera que encuentre la URL puede registrarse: no uses datos reales de pacientes ni presentes las cuentas como espacios privados.
- Antes de usar datos reales, requiere acceso restringido, HTTPS, almacenamiento persistente y respaldos. Advierte si el alojamiento usa almacenamiento efímero.

## Publicación

- Antes de crear recursos de alojamiento o incurrir en costos, explica el impacto y solicita autorización.
- Si ya existe un servicio de Render, confirma cómo obtiene la imagen y reutiliza ese servicio. No crees otro ni cambies su plan sin permiso.
- Para publicar una imagen Docker en Render, actualiza una etiqueta versionada y `latest`; indica que el usuario debe ejecutar **Manual Deploy** cuando corresponda.
- No afirmes que la aplicación publicada tiene cambios hasta comprobar la URL y `/health`. Añade al README solo URLs verificadas.
- En producción conserva `DRY_RUN=true` y `SEED_DEMO=false`, y guarda la clave de sesión en una variable de entorno segura.
