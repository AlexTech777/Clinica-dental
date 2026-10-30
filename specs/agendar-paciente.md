# Feature: Agendar paciente desde Agenda

## Problema
La asistente necesita crear una cita sin salir del panel y sin perder el uso habitual de Google Calendar. El botón de agenda debe tener un resultado real, validar los datos mínimos y dejar claro si la cita quedó en Google Calendar o solo localmente. Una acción ambigua o silenciosa genera duplicados y confusión para la atención diaria.

## Diseño de la solución
Desde la pantalla Agenda, “Agendar paciente” abre un formulario accesible con nombre, teléfono, tratamiento general, fecha, hora, duración y sesión actual/total opcionales. Al guardar, la aplicación valida los campos, crea o reutiliza el registro mínimo del paciente, guarda la cita y actualiza la vista. Si Calendar está conectado, crea un evento con título `Nombre - Tratamiento (X/Y)` cuando corresponda y `Tel: ...` en la descripción, conservando el ID del evento. Si Calendar no está configurado o falla, conserva la cita local y muestra “Pendiente de sincronización” con el motivo recuperable en el panel. No se almacenan notas clínicas.

## Criterios de aceptación
1. Desde Agenda, el botón abre un formulario que permite registrar todos los campos definidos y muestra errores comprensibles si faltan nombre, teléfono, tratamiento, fecha, hora o duración válida.
2. Al guardar una cita válida, esta aparece inmediatamente en Agenda, el paciente aparece en Pacientes y se muestra una confirmación con el estado de sincronización.
3. Con Calendar conectado, el evento usa el título y teléfono descritos, persiste el ID de Calendar y una nueva sincronización no duplica la cita; sin conexión, la cita local queda visible como pendiente.
4. Tras recargar la aplicación, la cita y su estado siguen presentes en SQLite; el registro contiene solo datos operativos mínimos y no incluye diagnóstico o notas clínicas.
5. El flujo funciona con teclado y en ancho móvil: modal/formulario con etiquetas, foco visible, acciones Guardar/Cancelar y estado de éxito o error anunciado.
