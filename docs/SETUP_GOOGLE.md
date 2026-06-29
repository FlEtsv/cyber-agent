# Setup Google — WEBPROD-015 (Suite) y WEBPROD-016 (Apps Script)

> Estos dos pasos necesitan TU interacción (Steve). El código ya está listo;
> solo faltan tus credenciales y autorizaciones.

---

## WEBPROD-015 — Gmail / Drive / Calendar (cómodo desde la web)

El backend (`app/google_suite.py`) y la UI (Ajustes → **Google**) ya están hechos:
estado, **Conectar**, **Desconectar** y acciones rápidas (no leídos / eventos / Drive).

### Lo que tienes que hacer (una vez)
1. Ve a **console.cloud.google.com** → crea (o elige) un proyecto.
2. **APIs y servicios → Biblioteca**: habilita **Gmail API**, **Google Drive API**
   y **Google Calendar API**.
3. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth**
   → tipo **App de escritorio** → descarga el JSON.
4. Guarda ese archivo como:
   ```
   C:\Users\steve\cyber-llm\agent-native\data\google_credentials.json
   ```
5. En la web → **Ajustes → Google → Conectar**. Se abrirá el navegador **en el PC**;
   **elige la cuenta de Google que quieras usar** y acepta los permisos.
6. Listo. "Desconectar" revoca y borra el token de este equipo (cierra la sesión).

> Privacidad: el token vive solo en `data/google_token.json` (gitignored). Eliges
> la cuenta en cada conexión; al desconectar se revoca.

---

## WEBPROD-016 — Apps Script (acciones avanzadas en tu Workspace) — LA ÚLTIMA

**Ya implementado y listo para desplegar.** No es un catálogo cerrado: es un
**puente flexible**. Cuando pidas algo de Google, el agente entra en tu Apps
Script y ejecuta acciones avanzadas arbitrarias — crear/modificar Sheets, Docs,
Slides, gestionar/coordinar Gmail, Drive, Calendar — vía:
- un **catálogo** de operaciones (`sheets_create`, `doc_append`, `slides_create`,
  `gmail_label`, `calendar_create`, …), o
- **`op:"exec"`** con código Apps Script a medida para cualquier cosa ("etc…").

Cada acción pasa por la **tarjeta de aprobación** del agente (tool `apps_script`
es peligrosa) → tú das el consentimiento en el momento.

### Tu parte (una vez)
1. Abre **script.google.com** → Nuevo proyecto.
2. Pega el contenido de **`integrations/apps_script/Code.gs`** (de este repo).
3. **Configuración del proyecto → Propiedades de script** → añade
   `SHARED_SECRET` = un secreto largo aleatorio.
4. **Implementar → Nueva implementación → Aplicación web**:
   - *Ejecutar como*: **Yo (mismo)** — las acciones corren en tu cuenta.
   - *Quién tiene acceso*: **Cualquiera** — necesario para que el PC pueda hacer
     POST. ⚠️ NO uses "Solo yo": exigiría login OAuth por petición y bloquearía
     al agente. La seguridad la da el `SHARED_SECRET` (sin él, `doPost` rechaza
     todo). Usa un secreto largo y aleatorio.
   - Autoriza los permisos (Sheets/Docs/Slides/Gmail/Drive/Calendar).
5. Copia la **URL `/exec`** de la implementación.
6. En el `.env` del PC añade y reinicia:
   ```
   APPS_SCRIPT_URL=https://script.google.com/macros/s/XXXX/exec
   APPS_SCRIPT_SECRET=<el mismo SHARED_SECRET>
   ```
7. Listo: pide al agente cosas como *"crea una hoja con estos datos"*, *"archiva
   y etiqueta los correos de facturas"*, *"haz una presentación con este guion"*.

> Backend: `app/apps_script.py` (conector) + tool `apps_script` (en DANGEROUS_TOOLS,
> categoría router `google`). Sin las dos variables de entorno, la tool avisa de
> que falta configurar y no hace nada.
