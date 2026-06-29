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

## WEBPROD-016 — Apps Script (controlar emails y ecosistema Google) — LA ÚLTIMA

La API de Google (015) ya cubre leer/enviar correo, Drive y Calendar. Apps Script
añade automatización avanzada (triggers, Sheets, acciones personalizadas) vía una
**webapp** que tú despliegas y que el agente llama con un secreto compartido.

### Lo que necesito decidir contigo antes de implementar
- ¿Qué acciones concretas quieres que el agente dispare por Apps Script?
  (ej.: etiquetar/archivar correos en lote, responder con plantillas, escribir en
  una Sheet, crear eventos, mover archivos…).
- Confirmar el modelo: webapp de Apps Script desplegada **como tú**, con un token
  secreto; el PC la llama por HTTPS.

### Tu parte (cuando definamos las acciones)
1. **script.google.com** → nuevo proyecto → pego el código que prepararé.
2. **Implementar → Nueva implementación → Aplicación web** → ejecutar **como tú**,
   acceso "solo yo".
3. Me pasas la **URL de la webapp** + el **secreto**; los pongo en `.env`
   (`APPS_SCRIPT_URL`, `APPS_SCRIPT_SECRET`) y conecto la tool.

> Plantilla de arranque existente: `relay/apps_script_email_code.gs` (envío de
> códigos por email). La ampliaremos con las acciones que elijas.
