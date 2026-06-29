# CyberAgent Web

La **interfaz web de CyberAgent** es un producto de primera clase, no un añadido del
relay. Es una PWA instalable que comparte el **mismo backend** que la app de
escritorio (PC): el modelo local en la GPU y la base de datos SQLite (fuente de la
verdad).

## Fuente única de verdad

Todo el código de la web vive **solo aquí** (`apps/web/`). Lo consumen dos backends:

| Consumidor            | Cómo sirve `apps/web`                                              |
|-----------------------|-------------------------------------------------------------------|
| **PC** (`app/api/server.py`) | Directo desde `apps/web` (mismo disco). `served/` queda local. |
| **Relay** (Cloud Run, `relay/main.py`) | `apps/web` → `relay/web` se sincroniza en `relay/deploy.ps1` (el contexto de Cloud Build es `./relay`). `relay/web/` es artefacto de build, no se versiona. |

> No dupliques estos archivos en `app/web/` ni en ningún otro sitio. El test
> `tests/test_web_ui_static.py::test_web_is_single_product_source` lo vigila.

## Archivos

- `index.html` — shell de la app (chat + workspace de carpetas).
- `login.html` / `login.css` — acceso (código por email + TOTP).
- `app.js` — lógica principal (chat, workspace, modelos, permisos).
- `ui.js` — helpers de UI (badges, voz, render).
- `style.css` — estilos (incluye diff, todos, carpetas, modales, fondos).
- `manifest.json` / `sw.js` — PWA (instalable, shell offline parcial).
- `icon-192.png` / `icon-512.png` — iconos.

## El relay es solo el cable

El relay reenvía mensajes web ↔ PC por WebSocket por `session_id`. No tiene lógica de
producto. Cambios de protocolo no requieren redeploy; cambios de UI sí (re-sincroniza
`apps/web`).

## Despliegue

```powershell
cd C:\Users\steve\cyber-llm\agent-native
.\relay\deploy.ps1 -Project cyberagent-web-2026
```
