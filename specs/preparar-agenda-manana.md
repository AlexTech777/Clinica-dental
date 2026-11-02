# SPEC: Preparar la agenda de mañana

## Problema

La asistente de un consultorio pequeño necesita cerrar el día sabiendo qué citas del día siguiente requieren confirmación, revisión del contacto o sincronización. Revisar una lista completa sin prioridades agrega trabajo y facilita que una cita pendiente pase inadvertida.

## Usuarios y alcance

- **Usuario principal:** asistente de recepción definida en [ICP y user persona](./icp-user-persona.md).
- **Pantalla:** Resumen, sin mezclar pacientes ni personas de la lista de espera.
- **Fuente de verdad:** las citas locales del panel; Google Calendar sigue siendo la agenda principal.
- **Datos permitidos:** nombre, teléfono, tratamiento general, horario y estado administrativo. No se muestran ni guardan datos clínicos.

## Solución

Agregar al Resumen una sección visual de preparación de la próxima jornada. Muestra el total de citas de mañana y cuenta las que requieren confirmación, revisión del contacto o sincronización. Las citas con un dato de contacto faltante aparecen primero, seguidas por problemas de Calendar y confirmaciones pendientes. Cada fila explica el motivo con texto y ofrece un acceso a Agenda filtrada para mañana.

## Criterios de aceptación

1. El Resumen muestra la fecha de mañana, el total de citas y contadores independientes de confirmación, contacto y Calendar.
2. Una cita pendiente, sin respuesta o por reprogramar aparece como **Confirmar cita**.
3. Una cita marcada para atención o cuyo paciente no tiene teléfono aparece como **Revisar contacto**.
4. Una cita con sincronización pendiente o en error aparece como **Pendiente en Calendar**; los registros únicamente locales no se presentan falsamente como errores.
5. Si una cita cumple más de una condición, aparece una sola vez con todos sus motivos; el listado prioriza primero los datos de contacto faltantes y luego el horario.
6. El enlace de la sección abre Agenda con el intervalo de mañana ya filtrado.
7. Con cero citas, se muestra un estado vacío explícito; con citas sin pendientes, se confirma que la agenda está al día.
8. La sección se adapta a pantallas móviles, conserva contraste y foco de teclado, y comunica estados mediante texto además del color.
9. Los cambios de la revisión no envían mensajes, no modifican citas y no almacenan datos adicionales.

## Métricas de éxito

Medir con una prueba piloto de dos semanas en un consultorio, revisando datos agregados y sin registrar información personal:

- **Tiempo de preparación:** mediana menor o igual a 2 minutos por jornada al terminar la semana piloto.
- **Citas preparadas:** al menos 90% de las citas del día siguiente quedan con estado de confirmación revisado antes del cierre.
- **Pendientes detectados:** 100% de las citas de mañana que cumplen los criterios de aceptación 2–4 aparecen en el resumen.
- **Claridad:** al menos 4 de cada 5 revisiones de la asistente identifican correctamente el siguiente paso sin abrir otra herramienta.

El panel no introduce analítica de pacientes: la medición se realiza mediante observación o un conteo manual agregado durante el piloto.
