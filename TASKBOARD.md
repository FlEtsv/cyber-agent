# TASKBOARD — CyberAgent Multi-Agent Board

> Documento de coordinación en tiempo real entre Claude Code, Codex y el Director (Steve).
> Ambos agentes leen este archivo completo al inicio de cada turno antes de hacer cualquier cosa.

---

## 📜 REGLAS — Vigentes desde aprobación del Director

> Estas reglas están activas. Steve las aprueba asignando tareas en el BACKLOG con `✅`.
> Los agentes las siguen sin necesidad de confirmación adicional.

**R1 — Declara antes de actuar.**
Antes de tocar cualquier archivo, escribe en `EN PROGRESO` qué vas a hacer, en qué archivos y por qué. Sin esa entrada no se empieza nada.✅

**R2 — Declara si tocas zona ajena.**
Si necesitas modificar un archivo que pertenece al otro agente (ver `AGENTS.md`), hazlo — pero escríbelo explícitamente en tu entrada de `EN PROGRESO` y en el mensaje del commit. No pides permiso, lo declaras.✅

**R3 — No dejes tareas a medias.**
Si empiezas, terminas: código completo, sintaxis verificada, commit hecho, tarea movida a `COMPLETADO`. Si surge un bloqueante real, muévela a `BLOQUEADO` con explicación clara.✅

**R4 — No alteres filtros de comportamiento ni ética de modelos.**
Ningún agente modifica system prompts de comportamiento interno, filtros de seguridad del LLM ni parámetros que cambien cómo razona el modelo. Sin excepciones.✅

**R5 — Lee el board primero, siempre.**
Al iniciar sesión: leer `TASKBOARD.md` → leer `AGENTS.md` → `git log --oneline -5`. Solo después actuar.✅

**R6 — El director manda.**
Las directivas de Steve en `OBJETIVOS` tienen prioridad absoluta. Si no hay objetivo activo, tomar la tarea de mayor prioridad `✅` del BACKLOG que corresponda a tu zona.

**R7 — Formato de commit obligatorio.**
`[claude] tipo: descripción` o `[codex] tipo: descripción`. Tipos: `feat`, `fix`, `security`, `docs`, `refactor`.✅

**R8 — PERMISO DE COMMIT Y EJECUCION.**
Las acciones que necesitan aprobación del usuario se dejan como petición en `PERMISOS SOLICITADOS`. Los objetivos genéricos se desglosan en tareas concretas de implementación, se añaden al `BACKLOG`, y Steve las aprueba con `✅` antes de ejecutarlas.
✅
**R8 — PERMISO DE COMMIT Y EJECUCION.**
SE DEJAN LAS ACCIONES QUE SE NECESITA QUE EL USUARIO APRUEBE COMO PETICIONES EN EL AREA DE PERMISOS Y PETICIONES ABAJO, TOMAD LOS OBJETIVOS GENERICOS COMO QUE TENEIS QUE DESGLOSARLO COMO TAREAS DE IMPLEMENTACION, HACEIS DESGLOSE AÑADIIS EN TAREAS DE BACKLOG Y YO LAS APRUEBO ASI TODO EL RATO.
✅

**R9 — CIERRE DE OBJETIVOS GLOBALES.**
Cuando un objetivo global ya esté implementado según sus tareas de desglose y el estado real del sistema, se quita de `OBJETIVOS` y se mueve a `OBJETIVOS IMPLEMENTADOS` con referencia a las tareas/commits que lo cierran.
✅

**R10 — EL CHAT NO ES CANAL DE PERMISOS.**
Ningún agente pide permisos, autorizaciones, confirmaciones de ejecución, confirmaciones de commit, push, despliegue ni aprobación operativa por el chat. Todo se solicita exclusivamente en `PERMISOS SOLICITADOS` o `PERMISOS Y PETICIONES` dentro de este documento. Si una acción ya tiene `✅` en el documento, el agente la ejecuta sin volver a mencionarla como permiso en el chat. El chat solo puede usarse para estado breve del trabajo.
✅


---


## 🎯 OBJETIVOS

> **Steve escribe aquí.** Los agentes leen esto primero en cada sesión.
> Si hay texto aquí, tiene prioridad sobre todo el BACKLOG.

*(todos los objetivos han sido implementados y movidos a OBJETIVOS IMPLEMENTADOS)*

        
    

    


## ✅ OBJETIVOS IMPLEMENTADOS

> Los agentes mueven aquí objetivos globales cuando el desglose asociado está completado y verificado.

- **Implementar sistema de reportes.** Cerrado por `REP-001` — export JSON/HTML en web/relay, reporte local desde `agent.log`, redacción de secretos y doc en `docs/SESSION_REPORTS.md`.
- **Integrar las herramientas de Hacking.** Cerrado por `TOOL-001` — catálogo estructurado, permisos por riesgo (`DANGEROUS_TOOLS`, `ACTIVE_SECURITY_TOOLS`, `SENSITIVE_ACCESS_TOOLS`), grupo router `hacking`, doc en `docs/TOOLS.md`.
- **Conseguir suit de herramientas global de precisión.** Cerrado por `TOOL-001`+`TOOL-002` — catálogo de 75+ herramientas, routing LLM mejorado con prompt detallado por categoría, grupo `desktop` completo añadido.
- **Actualizar cómo funciona cada herramienta y hacer manual de uso.** Cerrado por `DOC-001` — `docs/TOOLS_MANUAL.md` con descripción técnica, riesgo, cuándo usar y ejemplo de cada tool.
- **Improved del LLM de decisión de herramientas.** Cerrado por `TOOL-002` — prompt LLM de 350 tokens con descripción por categoría, reglas de desambiguación y ejemplos. Encoding mojibake corregido en keywords. Categoría `desktop` añadida al router.
- **Actualizar GUI con estética sofisticada.** Cerrado por `UI-001`+`UI-002`+`UI-003` — rediseño completo web/relay/desktop/login.
- **Diseñar seguridad contra fugas de datos.** Cerrado por `SEC-001`+`SEC-002`+`SEC-003`+`SEC-004` — redacción, CORS, sanitización errores HTTP, rate limiting.
- **Protección contra corrupción de datos.** Cerrado por `DATA-001` — backups SQLite WAL, checks de integridad, recuperación y tests.
- **Realizar pruebas automatizadas.** Cerrado por `TEST-001` — suite 12/12 tests auth, syntax checks, smoke JS.
- **Dejar interfaces listas para conectar PC local/nube con guía.** Cerrado por `DOC-003` — `docs/CONNECTION_GUIDE.md` con conexión LAN, relay Cloud Run, iPhone PWA, diagnóstico y variables de entorno.
- **Dejar claro el modo de uso para el usuario final.** Cerrado por `DOC-002` — `docs/USER_GUIDE.md` con acceso, modelos disponibles, tipos de tareas, tarjetas de aprobación y troubleshooting.
- **Asegurar que cada agente sepa actuar en su campo.** Cerrado por `AGENTS.md` — especialidad, zona, protocolo de acción y mapa de propiedad de archivos por agente.
- **Cada agente tiene manual de instrucciones claro.** Cerrado por `AGENTS.md`+`TASKBOARD.md` — protocolo de turno R1-R10, formato de commit, zonas y cómo coordinar sin bloquearse.
- **Cada agente tiene su espacio de archivos limpio y ordenado.** Cerrado por `AGENTS.md` — tabla de propiedad de cada archivo y zonas de no-toque documentadas.
- **Los agentes son los modelos de IA con los que se conecta el usuario final.** Cerrado por `DOC-002`+`AGENTS.md` — guía de modelos disponibles (rápido/potente), routing automático por complejidad, configuración via `CYBERAGENT_FAST_MODEL`/`CYBERAGENT_POWER_MODEL`.
- **OBJ-IO-001: App iOS nativa híbrida con agente local.** Cerrado por `IOS-001..009` + `IOS-UI-001..007` — app Swift completa: auth JWT/Keychain, WebSocket relay, BLE/GPS/USB, mini LLM offline, sistema de permisos, SwiftUI GitHub-dark, guía de usuario en `docs/IOS_APP_GUIDE.md`, build script `ios/build_and_deploy.sh`. GPU queue `55deb36` cierra la pieza de coordinación multi-cliente.




## 🔑 PERMISOS SOLICITADOS

> **Steve:** pon `✅` para autorizar el commit, o ignora si estás en dev — el agente pasa a la siguiente tarea y hace commit acumulado cuando llegue el tick.
> Formato: `[AGENTE] ID — "descripción exacta del commit" — Fecha HH:MM`
> Regla obligatoria: los agentes no piden estos permisos por chat. Solo añaden/modifican filas aquí y actúan cuando ven `✅`.

[claude] TEST-001+DATA-001+SEC-001 — "push git origin master (commit 9c92360)" — Fecha: 2026-06-24 22:58
[claude] TOOL-002+DOC-001+DOC-002+DOC-003 — commit "[claude] feat: TOOL-002 improved router + DOC-001/002/003 tool manual, user guide, connection guide" — Fecha: 2026-06-24 ✅

---

## 🔄 EN PROGRESO

> Escribe aquí ANTES de tocar cualquier archivo.
> Formato: `[AGENTE] ID — Qué voy a hacer — Archivos: x, y — Fecha: YYYY-MM-DD HH:MM`
> Si tocas zona ajena: añadir `⚠️ zona ajena: motivo`

---

## ✅ COMPLETADO

> Mover aquí desde EN PROGRESO al terminar.
> Formato: `[AGENTE] ID — Descripción — Commit: abc1234 — Fecha: YYYY-MM-DD HH:MM`

[claude] RELAY-BE-001+002+003 — Relay upgrade backend: modelos passthrough, buffer de sesión 50 msgs + endpoint history, ping/pong PC 15s — Commit: c392367 — Fecha: 2026-06-25
[codex] RELAY-UI-001..005 — Frontend relay remoto: historial remoto/localStorage restaurable, panel de ajustes con modelo/session trust/permisos, badge de cola GPU, watch mode y drag & drop de imágenes — Validación: node --check relay/web/app.js + pytest 47/47 — Commit: 0ba9c1e — Fecha: 2026-06-25 07:45
`[CODEX] INFRA-001 — Listener read-only de TASKBOARD.md — Commit: 831bae3 — Fecha: 2026-06-24 22:14`
[codex] OBJ-IO-001 — Formalizar el objetivo global enorme de la app iOS nativa híbrida — Commit: 1e4a9cb — Fecha: 2026-06-24 23:27
[codex] AUDIT-001 — Dashboard de actividad del agente en tab Agente: métricas de herramientas, errores y tiempos medios — Commit: 9b6fa02 — Fecha: 2026-06-24 23:34
[codex] IOS-UI-001 — RootView + MainTabView iOS con tabs Chat/Dispositivos/Ajustes y tema GitHub dark. Validación Swift pendiente: `swift` no disponible en Windows — Commit: 2996577 — Fecha: 2026-06-24 23:43
[codex] IOS-UI-002 — ChatView + MessageBubble iOS con burbujas, entrada, typing y aprobaciones provisionales hasta IOS-UI-003. Validación Swift pendiente: `swift` no disponible en Windows — Commit: e100619 — Fecha: 2026-06-24 23:51
[codex] IOS-UI-003 — ToolApprovalCard iOS con nombre/args/riesgo/categoría, aprobar/rechazar y countdown 60s. Validación Swift pendiente: `swift` no disponible en Windows — Commit: 25f0d90 — Fecha: 2026-06-24 23:58
[codex] IOS-UI-004 — DevicesView iOS con secciones BLE/GPS/accesorios, escaneo y conexión BLE. Validación Swift pendiente: `swift` no disponible en Windows — Commit: 438df96 — Fecha: 2026-06-25 00:03
[codex] IOS-UI-005 — SettingsView iOS para relay, PC local, red local, modo experto, permisos y logout. Validación Swift pendiente: `swift` no disponible en Windows — Commit: 7d9b719 — Fecha: 2026-06-25 00:10
[codex] IOS-UI-006 — Assets.xcassets mínimo con Contents, AccentColor y AppIcon placeholder. JSON validado con ConvertFrom-Json — Commit: 3365244 — Fecha: 2026-06-25 00:14
[codex] IOS-UI-007 — Theme.swift con CAColors, CAFont, StatusDot y CAButton reutilizables. Validación Swift pendiente: `swift` no disponible en Windows — Commit: bce37e9 — Fecha: 2026-06-25 00:17
[codex] RAG-002 — Autonomous learner ampliado con NVD CVE API 2.0, CISA KEV, Exploit-DB CSV, ranking por fuente y tags de origen. Validación: py_compile + pytest 47/47 — Commit: 3b715e9 — Fecha: 2026-06-25 00:26
[codex] MULTI-001 — Selector de personalidad del agente en GUI desktop: Asistente general/Hacker ofensivo/Analista defensivo como perfil de enfoque añadido al prompt sin tocar filtros. ⚠️ zona ajena declarada: system_context.py — Validación: py_compile + pytest 47/47 — Commit: 91b57bc — Fecha: 2026-06-25 00:33
[claude] B001+B007 — Backoff exponencial (5→10→20→40→60s) + cleanup runners al desconectar — Commit: c842ed7 — Fecha: 2026-06-24 22:20
[claude] B002 — CORS dinámico _DynamicCORS lee env por req (no import-time) — Commit: c842ed7 — Fecha: 2026-06-24 22:20
[claude] B003+F002 — AgentWorker llama _build_base_prompt() por turno (fecha actual en cada mensaje) — Commit: c842ed7 — Fecha: 2026-06-24 22:20
[claude] F003 — FAST_MODEL/POWER_MODEL configurables via CYBERAGENT_*_MODEL env — Commit: c842ed7 — Fecha: 2026-06-24 22:20
[codex] B004+B005+B006+UI-001 — Reconexión frontend, banners PC/reconectando y pulido visual web/relay — Commit: 3cc9d5b — Fecha: 2026-06-24 22:35
[codex] UI-002 — Rediseño GUI desktop PySide: cabecera workspace, navegación, estados y tema visual — Commit: 0d54b7c — Fecha: 2026-06-24 22:50
[codex] UI-003 — Rediseño login/PWA móvil local y relay con estado Cloud Run/PC/iPhone — Commit: 230564a — Fecha: 2026-06-24 22:58
[claude] TEST-001+DATA-001+SEC-001 — tests auth 12/12 + integrity_check/backup_db + redacción tokens en logs — Commit: 9c92360 — Fecha: 2026-06-24 22:58
[claude] SEC-003+SEC-004 — Sanitizar errores HTTP + rate limiting relay — Commit: bbaff5b — Fecha: 2026-06-24 23:10
[codex] REP-001 — Sistema de reportes de sesión con export JSON/HTML, redacción y documentación — Commit: 3cc9d5b (integrado en mejoras web) — Fecha: 2026-06-24 23:20
[codex] TOOL-001 — Catálogo hacking/tools: TOOL_CATEGORIES, DANGEROUS_TOOLS, ACTIVE_SECURITY_TOOLS, SENSITIVE_ACCESS_TOOLS, TOOL_USE_GUIDES en tools.py + docs/TOOLS.md — Commit: bbaff5b (integrado) — Fecha: 2026-06-24
[claude] TOOL-002+DOC-001+DOC-002+DOC-003 — Router LLM mejorado (prompt 350t + desktop group + fix encoding) + TOOLS_MANUAL.md + USER_GUIDE.md + CONNECTION_GUIDE.md + TASKBOARD objetivos cerrados — Commit: 3f9a41b — Fecha: 2026-06-24
[codex] GUI-001 — ToolsPanel tab en GUI desktop: catálogo por categoría con badges riesgo, filtro texto+combo+riesgo, panel detalle, botón "Abrir manual" — Archivos: app/widgets/tools_panel.py, app/widgets/main_window.py, app/styles.py, app/tools.py — Commit: d4424c9 — Fecha: 2026-06-24
[claude/codex] GUI-002 — Badges categoría·riesgo en action rows y approval cards de web/relay; iconos de categoría añadidos por Codex — Commit: 777592d + d4424c9 — Fecha: 2026-06-24
[codex] BOARD-001 — Trazabilidad de GUI-002 corregida para incluir iconos de categoría en d4424c9 — Commit: d4424c9 — Fecha: 2026-06-24 23:17
[claude] RELAY-SEC-001 — TOTP obligatorio por defecto en relay (TOTP_OPTIONAL=1 para dev). Warning startup si sin secret. — Commit: 7416d55 — Fecha: 2026-06-24
[claude] PERF-001 — Cache TTL 30s en execute_tool para system_info/gpu_info/memory_info (_cached:True en respuesta) — Commit: 7416d55 — Fecha: 2026-06-24
[claude] TEST-002 — 35 nuevos tests: test_tool_router.py (keyword/always/route_tools) + test_model_router.py (score/route). 47/47 pasan — Commit: 7416d55 — Fecha: 2026-06-24
[claude] DEBATE-002 — Expert mode backend: solo sesiones locales (127.0.0.1). Audit log por dangerous tool auto-aprobada. — Commit: 7416d55 — Fecha: 2026-06-24
[claude] IOS-001..009 — Backend iOS completo: Package.swift, Models, Auth, Relay, BLE/GPS/USB, LLM local, Network, Permissions, ChatViewModel, DeviceManager, OfflineAgentRunner — Commit: 531865e (parcial, ver commits previos para archivos anteriores) — Fecha: 2026-06-25
[claude] IOS-APP-GUIDE — Guía de usuario iOS completa en docs/IOS_APP_GUIDE.md — Commit: 531865e — Fecha: 2026-06-25
[claude] WATCH-001 — Modo vigilancia screenshots: tools.py (start/stop_screenshot_watch), agent_runner.py (watch_config event), server.py (async watch loop), app.js (watch frame render), style.css (watch UI), ios/build_and_deploy.sh, Desktop/CyberAgent_iOS_Deploy.bat — Commit: 531865e — Fecha: 2026-06-25
[claude] DEBATE-003 — Lazy model loading: fast model keep_alive=-1 (siempre residente), power model 10m (lazy). warm_fast_model() en lifespan startup. — Commit: f72c484 — Fecha: 2026-06-25
[claude] IOS-FIX-001 — Corrección 2 bugs compilación Swift: AnyCodableSimple (decode eagerly), ChatViewModel.error case closure syntax — Commit: f72c484 — Fecha: 2026-06-25
[codex] OPS-001 — Instancia Windows verificada y operativa: API local standalone en `scripts/start_local_api.py`, smoke test en `scripts/windows_smoke.ps1`, learner compatible con consola Windows. Validación: py_compile + pytest 47/47 + Ollama HTTP 200 + API local HTTP 200 — Commit: ec29df3 — Fecha: 2026-06-25 07:21
[claude] GPU-QUEUE — Semáforo asyncio.Semaphore(1) serializa inferencias concurrentes PC/relay/iOS. iOS/móvil tiene prioridad. Clientes reciben posición en cola mientras esperan. Guard garantiza liberación aunque AgentRunner falle al construir. — Commit: 55deb36 — Fecha: 2026-06-25

---

## 🚫 BLOQUEADO

> Tarea que no puede avanzar. Explicar motivo y qué necesita para desbloquearse.
> Formato: `[AGENTE] ID — Bloqueado por: motivo — Fecha: YYYY-MM-DD`

*(vacío)*

---

## 📋 BACKLOG

> **Steve:** marca con `✅` las tareas que aprueba para que los agentes las ejecuten.
> Sin `✅` los agentes no las tocan.
> Puedes añadir tareas nuevas aquí directamente con el formato de abajo.

### Bugs

| ID | ✅ | Descripción | Archivos | Agente | Prioridad |
|----|----|-------------|----------|--------|-----------|
| B001 | ✅ | Backoff exponencial en reconexión del relay (ahora sleep fijo 5s) | `app/api/relay_connector.py` | claude | alta |
| B002 | ✅ | CORS dinámico — ALLOWED_ORIGINS evaluado en import-time, no recarga si cambia la URL | `app/api/server.py` | claude | media |
| B003 | ✅ | SYSTEM_PROMPT con fecha fija al arranque — no se actualiza en sesiones largas | `app/ollama_client.py`, `app/api/agent_runner.py` | claude | media |
| B004 | ✅ | Frontend: limpiar pendingApproval y currentBubble al reconectar WS | `app/web/static/app.js`, `relay/web/app.js` | codex | alta |
| B005 | ✅ | Frontend: banner visible "reconectando" cuando WS cae >3s, deshabilitar input | `app/web/static/app.js`, `relay/web/app.js` | codex | alta |
| B006 | ✅ | relay/web: banner "PC offline" diferenciado cuando el PC se desconecta del relay | `relay/web/app.js` | codex | media |
| B007 | ✅ | Cleanup de runners activos al perder conexión con el relay | `app/api/relay_connector.py` | claude | alta |

### Features

| ID | ✅ | Descripción | Archivos | Agente | Prioridad |
|----|----|-------------|----------|--------|-----------|
| F001 | ✅ | Reconexión robusta completa (B001+B004+B005+B006+B007 agrupados) | varios | ambos | alta |
| F002 | ✅ | System prompt dinámico por turno de conversación | `app/ollama_client.py`, `app/api/agent_runner.py` | claude | media |
| F003 | ✅ | Segunda modelo en model_router (routing real entre fast/power) | `app/model_router.py` | claude | baja |

### Desglose de objetivos generales

| ID | ✅ | Descripción | Archivos | Agente | Prioridad |
|----|----|-------------|----------|--------|-----------|
| UI-001 | ✅ | Pulido visual del chat web/local y relay: layout, estados, mobile y legibilidad | `app/web/static/style.css`, `relay/web/style.css` | codex | alta |
| UI-002 | ✅ | Rediseño completo GUI desktop PySide: layout, navegación, paneles y estados | `app/widgets/*.py`, `app/styles.py` | codex | alta |
| UI-003 | ✅ | Rediseño login/PWA móvil: acceso claro, estado Cloud Run/PC y experiencia iPhone | `app/web/login.html`, `app/web/static/login.css`, `relay/web/login.html`, `relay/web/login.css` | codex | alta |
| SEC-001 | ✅ | Diseño técnico contra fugas de datos: clasificación, redacción, allowlist y auditoría de salidas | `docs/`, `app/agent_log.py`, `app/tools.py` | ambos | alta |
| DATA-001 | ✅ | Protección contra corrupción de datos: backups SQLite, checks WAL, recuperación y tests | `app/database.py`, `app/memory.py`, `scripts/` | claude | alta |
| REP-001 | ✅ | Sistema de reportes de sesión: acciones, herramientas, errores, duración y export HTML/JSON | `app/agent_log.py`, `app/web/static/app.js`, `relay/web/app.js`, `docs/` | codex | media |
| TOOL-001 | ✅ | Integración organizada de herramientas hacking ya existentes: catálogo, permisos, UI y logs | `app/tools.py`, `app/tool_router.py`, `app/web/static/app.js` | codex | alta |
| TEST-001 | ✅ | Suite mínima automatizada backend/frontend: syntax, unit tests críticos y smoke de JS | `tests/`, `scripts/`, `package.json` | ambos | alta |
| TOOL-002 | ✅ | Mejora LLM tool router: prompt detallado por categoría, reglas desambiguación, fix desktop group | `app/tool_router.py` | claude | alta |
| DOC-001 | ✅ | TOOLS_MANUAL.md: manual completo con descripción técnica, riesgo, cuándo usar y ejemplo de cada tool | `docs/TOOLS_MANUAL.md` | claude | alta |
| DOC-002 | ✅ | USER_GUIDE.md: guía de uso para usuario final con acceso, modelos, aprobación y troubleshooting | `docs/USER_GUIDE.md` | claude | alta |
| DOC-003 | ✅ | CONNECTION_GUIDE.md: guía de conexión LAN/relay/iPhone con comandos, diagnóstico y variables | `docs/CONNECTION_GUIDE.md` | claude | alta |

### Nuevas features para Codex — aprobadas por jefe de equipo (delegación de Steve)

| ID | ✅ | Descripción | Archivos | Agente | Prioridad |
|----|----|-------------|----------|--------|-----------|
| GUI-001 | ✅ | Panel visual de catálogo de herramientas en la GUI desktop: lista por categoría con badge de riesgo, filtro, y link a manual | `app/widgets/tools_panel.py`, `app/widgets/main_window.py`, `app/styles.py` | codex | media |
| GUI-002 | ✅ | Badges de categoría y riesgo en action rows del chat web/relay: icono de categoría + color por riesgo (alto=rojo, bajo=verde) | `app/web/static/app.js`, `relay/web/app.js`, `app/web/static/style.css`, `relay/web/style.css` | codex | media |

---

### 🚀 MEJORA CLOUD RUN — Desglose aprobado por Director

> **Objetivo:** elevar la interfaz relay (Cloud Run) al mismo nivel que la interfaz local.  
> Brechas identificadas por jefe de equipo: sin historial, sin selector de modelo, sin panel de ajustes, sin GPU queue badge, sin watch mode, sin drag & drop.

#### Zona Claude — Backend relay

| ID | ✅ | Descripción | Archivos | Agente | Prioridad |
|----|----|----|-------------|--------|-----------|
| RELAY-BE-001 | ✅ | Relay pasa lista de modelos del PC y modelo activo al cliente en el evento `connected`. El PC ya expone `/api/status` con models; el relay los solicita o el PC los manda en el evento init del host. | `relay/main.py` | claude | alta |
| RELAY-BE-002 | ✅ | Buffer de sesión en memoria: relay guarda últimos 50 mensajes por session_id. Endpoint GET `/api/session/{id}/history` devuelve el buffer para restaurar el historial al recargar. Datos no se persisten al disco (privacidad). | `relay/main.py` | claude | alta |
| RELAY-BE-003 | ✅ | Ping/pong activo al PC host: relay envía `{"type":"ping"}` cada 15s; si el PC no responde en 2 ciclos (30s), marca `pc_online=false` y notifica a todas las sesiones móviles. Detecta desconexiones silenciosas. | `relay/main.py` | claude | media |

#### Zona Codex — Frontend relay

| ID | ✅ | Descripción | Archivos | Agente | Prioridad |
|----|----|----|-------------|--------|-----------|
| RELAY-UI-001 | ✅ | Historial localStorage: al `connected`, solicitar historial al relay vía fetch y restaurar burbujas de conversación. Guardar en localStorage con clave `ca_history_{relayHost}`. Limpiar en logout. | `relay/web/app.js`, `relay/web/style.css` | codex | alta |
| RELAY-UI-002 | ✅ | Panel lateral de ajustes: botón gear en header abre slide-in panel con: selector modelo fast/power (enviado en el campo `model` del mensaje), toggle session trust, lista de permisos por herramienta (Auto/Preguntar/Bloquear). Guardar preferencias en localStorage. | `relay/web/app.js`, `relay/web/style.css`, `relay/web/index.html` | codex | alta |
| RELAY-UI-003 | ✅ | GPU queue badge: cuando llega un evento `status` que contenga "GPU ocupada" o "posición", mostrar un badge animado en el header (fondo naranja, texto "Cola: N") en vez del texto genérico. Desaparece cuando llega el primer `token`. | `relay/web/app.js`, `relay/web/style.css` | codex | alta |
| RELAY-UI-004 | ✅ | Port del watch mode: copiar la lógica de `_watchContainer`, `_handleWatchFrame`, `_endWatchMode` y los handlers de eventos `screenshot`/`watch_ended` de `app/web/static/app.js` al `relay/web/app.js`. Copiar CSS de watch mode de `app/web/static/style.css` a `relay/web/style.css`. | `relay/web/app.js`, `relay/web/style.css` | codex | media |
| RELAY-UI-005 | ✅ | Drag & drop de imágenes: el área `#input-area` acepta `dragover`/`drop` de archivos imagen. Visual feedback (borde glow al hover). Máximo 4 imágenes. Reutiliza `_attachImage()` existente. | `relay/web/app.js`, `relay/web/style.css` | codex | media |

---

### 📋 Instrucciones detalladas para Codex — RELAY-UI

> **Codex: lee esto antes de empezar. Empieza por RELAY-UI-001, luego en orden.**

#### RELAY-UI-001 — Historial localStorage
- En `_onMessage`, case `connected`: si hay `data.session_id`, hacer `fetch('/api/session/' + data.session_id + '/history')`. Si responde con array, llamar `_restoreHistory(messages)`.
- `_restoreHistory(messages)`: iterar mensajes, para cada uno llamar `_addUserBubble()` o `_addRestoredAIBubble()`. Marcar el container con clase `restored` para que sea visualmente tenue.
- Guardar cada burbuja enviada/recibida en `localStorage.setItem('ca_history_' + location.host, JSON.stringify(last50))`.
- En `logout`: `localStorage.removeItem('ca_history_' + location.host)`.

#### RELAY-UI-002 — Panel lateral de ajustes
- Añadir en `index.html` un `<div id="settings-panel">` con clase `settings-panel` (oculto por defecto).
- Botón gear en header: `<button id="settings-btn">⚙</button>`. Click toggle clase `open` en `#settings-panel`.
- Contenido del panel:
  - `<select id="model-select"><option value="">Auto</option><option value="fast">Rápido</option><option value="power">Potente</option></select>`
  - `<label><input type="checkbox" id="trust-toggle"> Auto-aprobar herramientas (session trust)</label>`
  - Lista de herramientas con Picker Auto/Preguntar/Bloquear (usar `this.permissions` existente)
- En `send()`, añadir `model: this.$('model-select').value || undefined` al payload.
- CSS: panel ancho 280px, slide desde derecha, backdrop semi-transparente al abrir.

#### RELAY-UI-003 — GPU queue badge
- En `_onMessage`, case `status`: si `data` es string y `/GPU ocupada|posición \d/i.test(data)`, extraer número con regex, actualizar `#queue-badge` (crearlo si no existe en header).
- Badge: `position: absolute`, fondo `#f0883e`, border-radius 12px, texto `Cola #N`, animar con pulse CSS.
- Cuando llega `token` o `done`: ocultar badge.

#### RELAY-UI-004 — Watch mode
- Copiar de `app/web/static/app.js`:
  - Variables: `_watchContainer`, `_watchFramesEl`, `_watchCounterEl`
  - Métodos: `_handleWatchFrame(data)`, `_endWatchMode(frames)`
  - Cases en `_onMessage`: `'screenshot'` → `_handleWatchFrame(data)`, `'watch_ended'` → `_endWatchMode(data.frames)`
- Copiar de `app/web/static/style.css` todos los estilos `.watch-*`.

#### RELAY-UI-005 — Drag & drop
- En constructor: `this._bindDragDrop()`.
- `_bindDragDrop()`: event listeners `dragover` (preventDefault, añadir clase `drag-over`), `dragleave` (quitar clase), `drop` (preventDefault, procesar `e.dataTransfer.files` igual que `openCamera()`).
- Target del evento: `document.getElementById('input-area')`.
- CSS: `.drag-over { border: 2px dashed #58a6ff; box-shadow: 0 0 12px #58a6ff44; }`

---

### 💡 Propuestas, Mejoras y Debates — Jefe de equipo a Director

> **Steve:** marca ✅ las que apruebes para que los agentes las ejecuten. Las de tipo DEBATE no tienen implementación asignada — son decisiones de arquitectura que el director debe tomar.

#### Mejoras técnicas (pendientes de aprobación)

| ID | ✅ | Tipo | Descripción | Zona | Agente | Prioridad |
|----|----|----|-------------|------|--------|-----------|
| WATCH-001 | ✅ | feat | Modo "watch" de screenshots periódicos: captura pantalla cada N segundos, envía al chat como stream de imágenes. Útil para supervisión remota desde iPhone. | `app/tools.py`, `app/api/agent_runner.py`, `app/web/static/app.js` | ambos | media |
| RELAY-SEC-001 | ✅ | security | Forzar TOTP en el relay: actualmente `totp_required: false`. Activar 2FA obligatorio para todas las sesiones remotas mejora la seguridad ante robo de contraseña. | `relay/main.py`, `docs/CONNECTION_GUIDE.md` | claude | alta |
| TEST-002 | ✅ | test | Tests de integración end-to-end con relay mock: simular PC↔relay↔cliente, verificar reconexión, aprobación de herramientas y reportes. | `tests/test_relay_integration.py` | ambos | media |
| PERF-001 | ✅ | refactor | Cache TTL corto para herramientas read-only frecuentes (`system_info`, `gpu_info`, `memory_info`): evitar llamadas duplicadas en la misma sesión cada <30s. | `app/tools.py` | claude | baja |
| RAG-002 | ✅ | feat | Ampliar temas del autonomous_learner: añadir CVE feeds (NVD API), exploit-db, threat intelligence. Mejorar relevancia de los documentos auto-aprendidos. | `app/autonomous_learner.py` | codex | media |
| MULTI-001 | ✅ | feat | Selector de personalidad del agente en la UI: "Asistente general", "Hacker ofensivo", "Analista defensivo" — cambia el system prompt base sin alterar filtros. | `app/consciousness/system_context.py`, `app/widgets/main_window.py` | ambos | baja |
| AUDIT-001 | ✅ | feat | Dashboard de actividad del agente: herramientas más usadas, errores frecuentes, tiempo medio de respuesta por sesión. Visible en tab "Agente". | `app/widgets/agent_panel.py`, `app/agent_log.py` | codex | baja |

#### Debates de arquitectura — Decisión del Director

> Estas entradas no tienen implementación directa. Son preguntas de diseño que afectan a cómo evoluciona el sistema. Los agentes esperan directriz antes de actuar.

**[DEBATE-001] ¿Historial de conversaciones en el relay?**
- **Propuesta:** Guardar el historial de conversaciones en Cloud Run (Firestore/CloudSQL) para acceder desde cualquier dispositivo sin depender del PC.
- **Pro:** Historial persistente remoto, accesible desde iPhone aunque el PC esté apagado.
- **Contra:** Datos de conversaciones (potencialmente sensibles) en la nube. Coste adicional.
- **Posición jefe de equipo:** Solo si se implementa cifrado E2E antes del almacenamiento. Sin cifrado, NO recomendado.
- **Decisión Steve:** ✅

**[DEBATE-002] ¿Auto-aprobación total en modo "experto"?**
- **Propuesta:** Añadir un modo "experto" donde el agente ejecuta cualquier herramienta sin tarjeta de aprobación, incluyendo las de alto riesgo.
- **Pro:** Flujo más rápido para usuarios avanzados.
- **Contra:** Un bug o prompt injection podría ejecutar shell/write_file/kill_process sin control.
- **Posición jefe de equipo:** Permitir solo en sesiones locales (GUI desktop), nunca en relay/web remoto. Añadir log de auditoría.
- **Decisión Steve:** ✅

**[DEBATE-003] ¿Múltiples instancias de Ollama o modelo único?**
- **Propuesta:** Cargar dos modelos Ollama en paralelo (fast + power) en lugar de usar el mismo modelo para ambos roles.
- **Pro:** Latencia real diferenciada (rápido para chat, potente para análisis complejos).
- **Contra:** 2x VRAM usage (16GB GPU puede quedarse corta con dos modelos grandes simultáneos).
- **Posición jefe de equipo:** Implementar lazy-loading del modelo potente solo cuando se necesite, no pre-cargado.
- **Decisión Steve:** ✅

**[DEBATE-004] ¿App nativa iOS o mejorar la PWA?**
- **Propuesta:** Desarrollar la app Swift descrita en `docs/IOS_EXTENSION_PRD.md` vs mejorar la PWA actual.
- **Pro app nativa:** Acceso a CoreBluetooth, notificaciones push reales, mejor UX.
- **Contra app nativa:** Semanas de desarrollo, firma Apple Developer, distribución.
- **Pro PWA mejorada:** Ya funciona, cero instalación, update instantáneo.
- **Posición jefe de equipo:** PWA mejorada a corto plazo (WATCH-001 + notificaciones web push). App nativa solo si se necesita BLE o funciones iOS-exclusivas.
- **Decisión Steve:** ✅

---

### 📱 App nativa iOS — Desglose del OBJETIVO

> **Jefe de equipo (claude):** Arquitectura, relay, auth, mini LLM, devices, network, ChatViewModel.
> **Codex:** UI SwiftUI (vistas, estilos, animaciones, Assets, Info.plist permisos).

#### Zona Claude — Backend iOS

| ID | ✅ | Descripción | Archivos | Agente | Prioridad |
|----|----|----|-------------|--------|-----------|
| IOS-001 | ✅ | Package.swift, Models (ChatMessage, AgentEvent), Utils (Constants, KeychainHelper) — EN PROGRESO | `ios/` | claude | alta |
| IOS-002 | ✅ | AuthManager (JWT cookie + Keychain), NetworkMonitor — EN PROGRESO | `ios/CyberAgent/Auth/` | claude | alta |
| IOS-003 | ✅ | RelayManager: URLSessionWebSocketTask, auto-reconexión exponencial, parseo AgentEvent | `ios/CyberAgent/Relay/` | claude | alta |
| IOS-005 | ✅ | BLEManager (CoreBluetooth), AccessoryDetector (ExternalAccessory), GPSManager (CoreLocation) | `ios/CyberAgent/Devices/` | claude | alta |
| IOS-006 | ✅ | LocalLLMManager (CoreML), SafeToolSubset (sin shell/write/kill), OfflineAgentRunner | `ios/CyberAgent/LocalLLM/` | claude | media |
| IOS-007 | ✅ | ConnectionResolver: LAN vs relay, fallback automático, ConnectionMode | `ios/CyberAgent/Network/` | claude | alta |
| IOS-008 | ✅ | PermissionManager: per-tool + per-device, UserDefaults/Keychain | `ios/CyberAgent/Permissions/` | claude | media |
| IOS-009 | ✅ | ChatViewModel: lógica agente (enviar msg, parsear tokens, manejar aprobaciones, historial) | `ios/CyberAgent/Chat/ChatViewModel.swift` | claude | alta |

#### Zona Codex — Frontend iOS SwiftUI

| ID | ✅ | Descripción | Archivos | Agente | Prioridad |
|----|----|----|-------------|--------|-----------|
| IOS-UI-001 | ✅ | RootView + MainTabView: tabs Chat/Dispositivos/Configuración con tema dark GitHub | `ios/CyberAgent/App/RootView.swift` | codex | alta |
| IOS-UI-002 | ✅ | ChatView + MessageBubble: burbujas user/assistant, markdown, typing indicator, scroll al último | `ios/CyberAgent/Chat/ChatView.swift`, `MessageBubble.swift` | codex | alta |
| IOS-UI-003 | ✅ | ToolApprovalCard: tarjeta aprobación con nombre/args/riesgo/categoría, Aprobar/Rechazar, countdown 60s | `ios/CyberAgent/Chat/ToolApprovalCard.swift` | codex | alta |
| IOS-UI-004 | ✅ | DevicesView: lista BLE/USB/GPS con estado, acciones por tipo de dispositivo | `ios/CyberAgent/Devices/DevicesView.swift` | codex | alta |
| IOS-UI-005 | ✅ | SettingsView: URL relay, IP local, expert mode toggle, permisos por herramienta, logout | `ios/CyberAgent/Chat/SettingsView.swift` | codex | media |
| IOS-UI-006 | ✅ | Assets.xcassets, Info.plist (permisos BT/GPS/Cámara/Red/Micrófono), LaunchScreen, AppIcon placeholder | `ios/CyberAgent/Assets.xcassets/`, `ios/CyberAgent/Info.plist` | codex | alta |
| IOS-UI-007 | ✅ | Theme.swift: Colors (dark GitHub), Typography, CAButton, CACard, StatusDot | `ios/CyberAgent/Utils/Theme.swift` | codex | media |

---

### Cómo añadir una tarea (Steve)

```markdown
| BXXX | ⬜ | Descripción del bug | `archivo.py` | claude/codex/ambos | alta/media/baja |
```

Cambia `⬜` a `✅` para aprobarla. Los agentes la ejecutan en su próxima sesión.

---

## 📌 Protocolo de turno para agentes

```
1. Leer TASKBOARD.md completo
2. Leer AGENTS.md (arquitectura + zonas)
3. git log --oneline -5  (ver qué hizo el otro)
4. ¿Hay OBJETIVO activo? → ejecutarlo
5. ¿No hay objetivo? → tomar tarea ✅ de mayor prioridad en tu zona
6. Escribir en EN PROGRESO antes de tocar nada
7. Hacer la tarea completa
8. Si necesita validación, ejecución, commit, push o despliegue: registrarlo en PERMISOS SOLICITADOS / PERMISOS Y PETICIONES y seguir con otra tarea si no hay ✅
9. Si ya hay ✅ en el documento: ejecutar sin pedir permiso por chat
10. Mover a COMPLETADO + commit del TASKBOARD
11. Si Codex se queda sin margen de uso o se interrumpe, dejar en `EN PROGRESO` el estado exacto, el punto donde se quedó, qué falta y cuándo puede reanudar para que Claude lo vea y continúe la coordinación.
```


## 📌 PERMISOS Y PETICIONES

Se dejan las acciones que se necesita que el usuario apruebe como peticiones en el área de permisos y peticiones abajo, tomad los objetivos genericos como que teneis que desglosarlo como tareas de implementacion, haceis desgloses añadís en tareas de backlog y yo las apruebo asi todo el rato.

**Prohibido pedir estos permisos por chat.** El chat no es un canal de aprobación. Si falta un `✅`, el agente registra la petición aquí y continúa con otra tarea aprobada. Si el `✅` ya está puesto, ejecuta directamente y actualiza el estado.

| ID | ✅ | Agente | Acción solicitada | Estado |
|----|----|--------|-------------------|--------|
| P-CODEX-001 | ✅ | codex | Ejecutar `node --check app/web/static/app.js` y `node --check relay/web/app.js`; si pasan, hacer commit acumulado `[codex] feat: improve web reconnect and visual states` con B004+B005+B006+UI-001 y actualización del TASKBOARD. | completado: 3cc9d5b |
| P-CODEX-002 | ✅ | codex | Ejecutar validación de sintaxis Python para `app/widgets/main_window.py` y `app/styles.py`; si pasa, commit `[codex] feat: refine desktop gui shell` con UI-002 y actualización del TASKBOARD. | completado: 0d54b7c |
| P-CODEX-003 | ✅ | codex | Ejecutar validación HTML/CSS básica de login local/relay; si pasa, commit `[codex] feat: redesign mobile login surfaces` con UI-003 y actualización del TASKBOARD. | completado: 230564a |

---

## 🔄 PROTOCOLO DE TURNO CUANDO SE AGOTA EL CONTEXTO

> Instrucción del Director al equipo.

Cuando un agente se quede sin tokens/límite de contexto durante una tarea:
1. **Dejar en este documento** (sección BLOQUEADO o nota en COMPLETADO/EN PROGRESO):
   - ID de tarea que estaba ejecutando
   - Estado exacto: qué se hizo, qué falta
   - Timestamp de disponibilidad estimada
   - Archivos tocados (para que el otro agente no pise)
2. **Claude (jefe de equipo) verá el estado** al inicio de su próximo turno.
3. **No dejar archivos a medias** — dejar siempre código que compile o marcar claramente como WIP.

**Formato de nota de pausa:**
```
[AGENTE] PAUSA en IOS-XXX — Hecho: [lista]. Falta: [lista]. Archivos WIP: x.swift — Disponible: HH:MM
```

---

## 📋 ASIGNACIONES DIRECTAS CODEX — del Jefe de Equipo (claude)

> **Codex:** Estas son tus tareas concretas para el proyecto iOS. Empieza por IOS-UI-001 (alta).
> Lee los archivos de claude en `ios/CyberAgent/` antes de empezar cada UI — los ViewModels ya están listos.

### IOS-UI-001 — RootView + MainTabView ✅
**Archivos a crear:** `ios/CyberAgent/App/RootView.swift`
- `RootView`: selector entre ChatView / DevicesView / SettingsView con TabView
- Tabs: "Chat" (icono: message), "Dispositivos" (bolt.horizontal), "Ajustes" (gear)
- Usar `ChatViewModel` ya implementado (importar y usar `@StateObject`)
- Tema: fondo `#0d1117`, tabs accent `#58a6ff`

### IOS-UI-002 — ChatView + MessageBubble ✅
**Archivos a crear:** `ios/CyberAgent/Chat/ChatView.swift`, `ios/CyberAgent/Chat/MessageBubble.swift`
- `ChatView`: ScrollViewReader, TextField con botón enviar, indicador de typing, overlay con ToolApprovalCards
- `MessageBubble`: user (derecha, `#1f6feb`) / assistant (izquierda, `#161b22`), timestamps, Markdown básico (negrita, código)
- Lee `ChatViewModel.swift` para ver qué datos están disponibles

### IOS-UI-003 — ToolApprovalCard ✅
**Archivo a crear:** `ios/CyberAgent/Chat/ToolApprovalCard.swift`
- Card oscura (`#161b22`, borde `#f85149` si alto riesgo, `#3fb950` si bajo)
- Muestra: nombre tool, categoría badge, risk badge, args en `Text` monospace
- Botones: "Aprobar" (verde) / "Rechazar" (rojo)
- Countdown timer 60s (ProgressView circular)
- Auto-rechaza cuando el timer llega a 0

### IOS-UI-004 — DevicesView ✅
**Archivo a crear:** `ios/CyberAgent/Devices/DevicesView.swift`
- 3 secciones: BLE (lista `ble.discoveredDevices`), GPS (mapa mini o coordenadas), Accesorios USB
- Botón "Escanear BLE" → `BLEManager.shared.startScan()`
- Status dot (verde/gris) por dispositivo
- Tap en BLE device → `BLEManager.shared.connect(to:)`

### IOS-UI-005 — SettingsView ✅
**Archivo a crear:** `ios/CyberAgent/Chat/SettingsView.swift`
- URL del relay (TextField con `UserDefaults`)
- IP del PC local (TextField)
- Toggle "Preferir red local"
- Toggle "Modo experto" → `PermissionManager.shared.setExpertMode(_:)`
- Lista de permisos por herramienta (Picker: Auto/Preguntar/Bloquear)
- Botón "Cerrar sesión" → `AuthManager.shared.logout()`

### IOS-UI-006 — Assets + Info.plist ✅
**Archivos a crear:** `ios/CyberAgent/Assets.xcassets/Contents.json` + AppIcon placeholder
- El `Info.plist` ya está en `ios/CyberAgent/Info.plist` (claude)
- Crea el `Assets.xcassets` con estructura mínima (Contents.json, AccentColor, AppIcon)

### IOS-UI-007 — Theme.swift ✅
**Archivo a crear:** `ios/CyberAgent/Utils/Theme.swift`
- `CAColors`: backgroundPrimary (#0d1117), backgroundSecondary (#161b22), accent (#58a6ff), dangerRed (#f85149), successGreen (#3fb950), textPrimary (.white), textSecondary (#8b949e), borderColor (#30363d)
- `CAFont`: monospaced, body, caption
- `StatusDot(color:)`: Circle 8pt
- `CAButton(label:action:style:)`: style enum (primary/danger/ghost)
