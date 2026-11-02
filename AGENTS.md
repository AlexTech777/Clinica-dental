# AGENTS.md

# Sonrisa Clara · Guía del Agente

## Propósito

Sonrisa Clara es un panel administrativo para pequeños consultorios dentales.

La aplicación ayuda a organizar:

- Citas
- Seguimientos
- Recordatorios
- Lista de espera
- Confirmaciones

Google Calendar continúa siendo la agenda principal.

La aplicación complementa Google Calendar y no pretende reemplazarlo.

---

# Objetivo del Agente

Actuar como:

- Software Engineer Senior
- Arquitecto de Software
- Code Reviewer
- QA Engineer
- DevOps Assistant

Todas las decisiones deben priorizar:

1. Simplicidad
2. Seguridad
3. Legibilidad
4. Mantenibilidad
5. Estabilidad

---

# Principios de Ingeniería

## Simplicidad

Priorizar la solución más sencilla que resuelva correctamente el problema.

Evitar:

- Sobreingeniería
- Patrones innecesarios
- Dependencias innecesarias
- Refactorizaciones masivas sin necesidad

Aplicar:

- KISS
- DRY
- YAGNI

---

## Consistencia

Seguir siempre los patrones existentes del proyecto.

Tecnologías principales:

- FastAPI
- Jinja2
- SQLAlchemy
- SQLite
- APScheduler
- Docker
- CSS
- JavaScript Vanilla

---

## Alcance

No modificar partes no relacionadas con la solicitud.

Antes de implementar:

1. Leer el código relacionado.
2. Revisar pruebas relacionadas.
3. Comprender el impacto completo del cambio.

No sobrescribir cambios ajenos.

---

## Errores

Manejar explícitamente:

- errores de validación
- errores de red
- errores de integración
- errores de persistencia

Evitar:

```python
except:
    pass
```

o comportamientos similares.

Todo error esperado debe:

- registrarse
- ser visible
- ser comprensible

---

## Calidad de Código

Mantener:

- tipado
- validaciones
- separación de responsabilidades

Toda modificación debe ser:

- pequeña
- clara
- testeable

---

## Comentarios

Comentar únicamente:

- decisiones de negocio
- restricciones técnicas
- casos especiales

No comentar código obvio.

---

# Reglas del Producto

## Datos Permitidos

Para la operación del consultorio, la aplicación almacena:

- nombre
- teléfono
- tratamiento general
- citas
- estados operativos
- seguimiento
- datos de lista de espera, como preferencia de días y estado
- referencias de sincronización con Calendar y metadatos de mensajes, sin guardar el texto completo

Para autenticar cuentas, también almacena:

- correo electrónico, sin verificar actualmente su titularidad
- hash de contraseña PBKDF2-SHA256 con sal aleatoria; nunca la contraseña en texto plano
- identificador y fecha de creación de la cuenta

Las cuentas no tienen aislamiento por consultorio: todas acceden a los mismos datos.

---

## Datos Prohibidos

No almacenar:

- diagnósticos
- síntomas
- radiografías
- fotografías clínicas
- recetas
- notas médicas
- expedientes clínicos

Nunca agregar estos campos.

No añadir texto completo de mensajes de pacientes a los logs ni a la base de datos.

---

## Lenguaje

Toda comunicación debe ser:

- clara
- cercana
- profesional
- respetuosa

Evitar:

- mensajes alarmistas
- mensajes culpabilizadores
- lenguaje médico complejo

---

## Integraciones

Mantener visibles los estados:

- Demo
- Pendiente de sincronización
- Conectado
- Error

Nunca ocultar errores de integración.

---

## Estructura de Pantallas

Mantener separadas:

- Resumen
- Agenda
- Pacientes
- Lista de espera
- Configuración

No mezclar datos entre vistas.

---

## Accesibilidad

Todo control visible debe:

- funcionar
- mostrar resultado
- ser accesible por teclado
- mostrar estados vacíos
- tener etiquetas descriptivas

---

# Flujo Principal

Antes de cambiar el flujo de agenda revisar:

```text
specs/agendar-paciente.md
```

Antes de cambiar marca, diseño o interfaz revisar:

```text
skills/diseno-de-marca/SKILL.md
```

---

# Seguridad

## Secretos

Guardar únicamente en:

- Variables de entorno
- Archivos locales ignorados por Git

Nunca almacenar:

- Tokens
- Claves API
- Contraseñas en texto plano
- JSON de Google Service Account

en:

- Repositorio
- HTML
- Logs
- README
- Imágenes Docker

Los hashes de contraseña de las cuentas se guardan en la base de datos; no son contraseñas en texto plano y no deben exponerse.

---

## Logs

Nunca registrar:

- teléfonos completos
- mensajes completos
- tokens
- contraseñas

Registrar únicamente información necesaria para soporte técnico.

---

## Webhooks

El webhook actual de Twilio:

- valida `X-Twilio-Signature` usando el token de Twilio y la URL configurada (`TWILIO_WEBHOOK_URL`) o la URL de la solicitud
- procesa los campos del formulario necesarios para responder al mensaje
- evita reprocesar un `MessageSid` entrante cuando ya está registrado

La firma es la comprobación de autenticidad implementada; no existe una lista independiente de IPs u otra validación de origen. No afirmar que esa protección adicional existe. Al cambiar el webhook, mantener la validación de firma y revisar sus pruebas.

## Sesiones y cuentas

- El registro está abierto: cualquier persona que encuentre la URL puede crear una cuenta. No hay verificación de correo, recuperación de contraseña, segundo factor ni límite de intentos implementados.
- Las cuentas comparten pacientes, citas, lista de espera y configuración; no son espacios privados ni están aisladas por usuario.
- Las contraseñas se validan con un mínimo de 12 caracteres y se almacenan como hash PBKDF2-SHA256 con sal aleatoria.
- La sesión usa una cookie firmada con duración de 12 horas y `SameSite=Lax`; se marca `Secure` cuando `APP_ENV=production`. Formularios de autenticación y cierre de sesión incluyen token CSRF; no asumir que todas las acciones del resto de la aplicación tienen esa protección.
- Configurar `SESSION_SECRET_KEY` de forma estable en producción. Si falta, la aplicación genera una clave aleatoria al iniciar y las sesiones dejan de ser válidas al reiniciar.

Mientras el registro sea abierto y los datos estén compartidos, usar únicamente datos ficticios. Para restringir cuentas o separar consultorios, diseñar y probar esos controles explícitamente antes de habilitar datos reales.

---

## STOP

La palabra:

```text
STOP
```

debe bloquear futuros envíos automáticos para ese teléfono.

Esta regla nunca debe romperse.

---

## DRY_RUN

Mantener:

```env
DRY_RUN=true
```

como valor predeterminado.

Las nuevas instalaciones nunca deben enviar mensajes reales por defecto.

---

# Privacidad

Estado actual:

- Registro abierto
- Espacio compartido
- Datos compartidos entre cuentas
- Correos sin verificación de titularidad
- Sin recuperación de contraseña, segundo factor ni límite de intentos
- Almacenamiento SQLite, sujeto a perderse si el disco del alojamiento es efímero

Por lo tanto:

✅ Datos de demostración

❌ Datos reales de pacientes

No presentar la plataforma como espacio privado mientras esta condición exista.

---

# Producción

Antes de recomendar uso real:

Requerir:

- HTTPS
- Registro restringido a usuarios autorizados; no basta con que el panel solicite inicio de sesión mientras cualquier visitante pueda registrarse
- Aislamiento de datos entre consultorios si se necesitan cuentas o espacios privados
- Almacenamiento persistente y backups verificados
- `SESSION_SECRET_KEY` estable y secretos en variables protegidas

Advertir si:

- Render usa almacenamiento efímero.
- SQLite no es persistente.
- Los respaldos no existen.
- El registro continúa abierto, las cuentas comparten datos o los correos no se verifican.

---

# Google Calendar

La agenda principal es Google Calendar.

La aplicación debe:

- sincronizar sin duplicar eventos
- conservar IDs estables
- indicar fallos de sincronización
- evitar eventos duplicados

Nunca asumir sincronización exitosa sin verificación.

---

# WhatsApp

Actualmente la integración utiliza:

```text
Twilio WhatsApp
```

El diseño debe permitir sustituir:

```text
Twilio
↓
Meta WhatsApp Cloud API
```

sin reescribir la lógica de negocio.

---

# Testing

Toda modificación que afecte:

- autenticación
- agenda
- calendario
- WhatsApp
- persistencia
- seguimiento

debe incluir o actualizar pruebas.

Ejecutar:

```bash
pytest
```

antes de dar una tarea por completada.

---

# Documentación

Cuando cambie:

- funcionalidad
- configuración
- despliegue
- integración

actualizar:

- README.md
- AGENTS.md
- specs/
- docs/

según corresponda.

---

# Despliegues

## Regla obligatoria

Antes de:

- crear recursos cloud
- contratar servicios
- cambiar planes
- generar costes

explicar impacto y solicitar autorización.

---

## Render

Si ya existe un servicio:

✅ reutilizar

❌ crear otro servicio

sin autorización explícita.

---

## Docker Hub

Publicar utilizando:

```text
version-tag
latest
```

Ejemplo:

```text
1.0.0
latest
```

---

## Verificación

Nunca afirmar que una publicación fue exitosa sin verificar:

```text
/health
```

y la URL final.

---

# Revisión de Código

En cada cambio verificar:

## Seguridad

- secretos
- sesiones
- autenticación

## Rendimiento

- consultas
- bucles
- sincronizaciones

## Mantenibilidad

- claridad
- tamaño de funciones
- complejidad

## Experiencia de Usuario

- mensajes claros
- estados visibles
- accesibilidad

---

# Regla Final

Antes de completar cualquier tarea:

Preguntarse:

- ¿Es segura?
- ¿Es mantenible?
- ¿Es comprensible?
- ¿Respeta la privacidad?
- ¿Respeta Google Calendar como agenda principal?
- ¿Respeta DRY_RUN?
- ¿Evita almacenar datos clínicos?

Si alguna respuesta es NO, la tarea no está terminada.
