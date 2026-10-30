# Plan de arquitectura (antes de implementar)
1. Aplicación server-rendered con FastAPI y Jinja2: navegación simple, sin frontend pesado.
2. SQLite/SQLAlchemy para citas, pacientes mínimos, espera, seguimiento y bitácora de mensajes.
3. El feature principal será agendar una cita con validación, paciente vinculado y estado de sincronización.
4. Google Calendar será un adaptador: cuenta de servicio compartida por el calendario; `DRY_RUN`/demo no requieren conexión.
5. Twilio se encapsula en un servicio sustituible; webhooks procesan respuestas e idempotencia.
6. APScheduler procesa sincronización, recordatorios, seguimiento y espacios liberados periódicamente.
7. Las pantallas Resumen, Agenda, Pacientes, Lista de espera y Configuración serán rutas/vistas separadas.
8. Las preferencias de tema se guardan en localStorage; configuración operativa y datos mínimos en SQLite.
9. Cualquier cita local creada sin Calendar configurado muestra `pendiente de sincronización`.
10. Incluye seed demo, `.env.example`, Docker Compose, README en español y tests unitarios/integración básicos.
11. Manejo de secretos solo por variables de entorno; credenciales nunca se incluyen en el repositorio.
12. Al finalizar: validar spec, correr tests solicitados y comprobar visualmente flujos en navegador.
