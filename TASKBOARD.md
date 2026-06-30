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

**OBJ-WEBPROD — La web como PRODUCTO PRINCIPAL (no extensión del relay).** (Steve, 2026-06-29)
La web pasa a ser el agente principal de Steve: producto de primera clase, mobile-first,
que comparte backend con el PC (modelo local + SQLite fuente de verdad) con el relay como
cable invisible. Coste Cloud Run mínimo. Desglose y estado en el BACKLOG → sección
"WEB COMO PRODUCTO PRINCIPAL" (`WEBPROD-001..015`). Reglas que Steve fijó por chat:
- Nuestro modelo se llama "**Modelo local**" en toda la UI.
- Footer por respuesta: "¿Es útil?" (verde) + "Escalar a superior". Escalera reactiva
  (la decide el usuario): programación → Codestral → Mistral Large; resto → Medium → Large.
- Mistral creación + interpretación de imágenes.
- Menú de gasto por mensaje (icono $ → modal con coste por tokens/€ individual y acumulado
  mensual de todos los modelos).
- Carpetas/categorías/proyectos con contexto; adjuntos por conversación (archivos/links/
  scripts), favoritos que persisten aunque se borre la conversación.
- Arreglar adjuntar imágenes (roto en web) y permitir adjuntos NO-imagen.
- Suite Google con una implementación cómoda y usable.

        
    

    


## 🚀 CYBERAGENT 2.0 — RELEASE EN CURSO

> Sesión 27-jun-2026 (Claude). Cerebro Mistral híbrido/fusionado + UI web responsive 2.0.
> Verificado en vivo con API key real: 15/15 pruebas de integración + 4/4 endpoints UI + 67/67 regresión.

### ✅ Hecho y verificado en esta sesión
- Cerebro Mistral (large/medium) como agente real con function-calling sobre las 82 tools locales; modos `auto`/`fused`/manual; fallback a local. Probado end-to-end (memory_info, system_info, fused).
- Herramientas nativas Mistral Studio: `web_search` real (Python 3.14.4 con fuente), `code_interpreter` (suma 100 primos=24133), image_generation, document_library.
- Routing con guardrails: tareas ofensivas/sensibles se quedan en LOCAL (Mistral las rechazaría); modelos avisados en el system prompt.
- Compactación: ancla de objetivo persistente + ctx configurable + resumen que preserva objetivo.
- Razonamiento separado de la respuesta (evento `reasoning`, panel atenuado) en ambos frontends + desktop.
- Documentos (PDF/HTML/MD/TXT) + `serve_file` + **auto-arranque de túnel Cloudflare** → "correr script/generar doc → URL pública" funciona solo (probado: trycloudflare devolvió enlace real).
- Web 2.0 responsive (PC+móvil): app-shell con navegación Chat/Herramientas/Archivos/Ajustes, brain badge del cerebro activo, catálogo de 82 tools con permisos, galería de archivos generados, voz TTS. Endpoints `/api/tools` y `/api/files` + anuncio por websocket relay.

### 📋 BACKLOG 2.0 — CARENCIAS DETECTADAS (pendiente aprobación Director con ✅)
> Respuesta a "¿qué NO puede hacer el agente?". Priorizado por impacto.

**P0 — Críticas**
- ✅ `BROWSER-001` HECHO — `browse_page` (Playwright+Chromium): JS, SPA, login, fill, click, screenshot→URL. Probado contra example.com.
- ✅ `GIT-001` HECHO — `git_op`: status/log/diff/branch/add/commit/push/pull/checkout/create_branch/clone (whitelist, sin shell).
- ✅ `INGEST-001` HECHO — `read_document`: PDF (pypdf), Excel (openpyxl), Word (python-docx), CSV, JSON, código. Probado.
- ✅ `SCHED-001` HECHO — `schedule_task`/`list_scheduled`/`cancel_scheduled` + motor `app/scheduler.py` (interval/at/file, acción tool/shell, persistente, opt-in). Ejecución verificada.
- ✅ `MSG-001` HECHO — `send_message` (email SMTP + Telegram), config por env, degradación clara. Categoría `messaging`.
- ✅ `HARDEN-001` HECHO — scheduler blindado: acciones shell/herramientas peligrosas requieren `allow_dangerous=true` explícito (no se agendan acciones sin supervisión por accidente).
- ✅ `INSTALL-001` HECHO — app nativa Windows: `installer/install_shortcut.ps1` (+ `make_icon.py`) crea icono .ico + accesos directos Escritorio/Menú Inicio (pythonw, sin consola), `-Autostart` y `-Uninstall`. Tray con Abrir/**Reiniciar**/Salir; single-instance ya existente (mutex). Instalado y verificado.
- ✅ `AUDIT-FUNC` HECHO — auditoría funcional 9/9: el modelo (Mistral) USA realmente cada tool vía el bucle del agente (read_document→ACME/4200€, git_op, browse_page→example.com, web_search→Canberra, schedule_task, generate_document+serve_file).

**P1 — Importantes**
- `SANDBOX-001` Ejecución de código en sandbox Docker local (aislar `run_python`/scripts no confiables del host).
- `DB-001` Conector SQL externo (Postgres/MySQL/SQLite remoto) con consultas parametrizadas.
- `VAULT-001` Gestor de secretos cifrado para credenciales de APIs de terceros (GitHub/Jira/cloud) usable por las tools.
- `OFFSEC-001` Seguridad ofensiva avanzada: wrappers de nmap NSE, sqlmap, hashcat, radare2/Ghidra, análisis pcap, fuzzing. (uso autorizado).
- `WINCTL-001` Control profundo de Windows: servicios start/stop, tareas programadas, reglas de firewall, usuarios.

**P2 — Complementarias**
- `VISION-001` Visión local estructurada (detección/comparación de objetos), no solo descripción.
- `AUDIO-001` STT/TTS server-side + transcripción de audio/vídeo.
- `ORCH-001` Orquestación multi-agente real (planner→workers especializados) más allá del modo fused.

---

## ✅ OBJETIVOS IMPLEMENTADOS

> Los agentes mueven aquí objetivos globales cuando el desglose asociado está completado y verificado.

- **Cerebro multi-backend + Mistral como agente (no solo consulta).** `app/brain.py` (streaming Mistral con function-calling, normalización de historial al contrato Mistral con `tool_call_id` de 9 alfanuméricos y saneo de huérfanos), dispatch en `agent_runner._stream_once` y `ollama_client._stream_once`, router con escalado a nube (`model_router.route`), modos `auto`/`fused`/`mistral-*` seleccionables en web (`relay_connector._announce_models`) y desktop (combo en `main_window`). Fallback automático a local si Mistral falla.
- **Integración de herramientas nativas de Mistral Studio.** `app/mistral_studio.py` (Conversations API: `web_search`, `code_interpreter`, `image_generation`, `document_library`), expuestas como tool `mistral_studio`; `web_search` ahora usa búsqueda real de Mistral con fallback DuckDuckGo. Tools cruzadas: Mistral usa las 82 locales por function-calling y el agente delega en local con `local_llm_consult`.
- **Fix de compactación que perdía el objetivo.** Ancla `## OBJETIVO PERSISTENTE` fijada en el system prompt (no se compacta), `MAX_CTX` configurable (16384 def.), presupuesto de prompt escalado, `RECENT_MESSAGES=18` y resumen que preserva el objetivo original (`memory.summarize_messages`).
- **Razonamiento separado de la respuesta final.** Nuevo evento/Signal `reasoning` (antes era `token`): web pinta panel atenuado y colapsable (`relay/web/app.js` + `style.css`), desktop indicador en barra de estado. Persona más natural + flujo "razonar sobre la verdad" en `_build_base_prompt`.
- **Entrega de resultados al usuario.** `app/documents.py` (PDF/HTML/MD/TXT vía reportlab/markdown) + `serve_file`/`/served` montado en `server.py` + URL pública del túnel (`tunnel.get_public_url`). Tools `generate_document` y `serve_file`. *(Pendiente del Director: definir MISTRAL_API_KEY en el entorno — sin ella el cerebro nube queda inactivo y cae a local.)*
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

[claude] AI..AN — Detección + re-ID + tracking + patrones + anomalías + Telegram Topics — Archivos: `app/security/detect.py`, `app/security/pets.py`, `app/security/reid.py`, `app/security/tracker.py`, `app/security/space_map.py`, `app/security/zones.py`, `app/security/patterns.py`, `app/security/predictor.py`, `app/security/anomaly.py`, `app/security/species_priors.py`, `app/comms/telegram_topics.py`, `app/comms/setup.py` — Fecha: 2026-06-30

[codex] AUTH-RECOVERY-005 — Recuperar acceso al relay y preparar login por email si hay proveedor SMTP: diagnosticar credenciales/TOTP desplegados, regenerar QR/credenciales si procede y mejorar flujo de recuperación sin romper auth actual — Archivos: `relay/main.py`, `relay/web/login.html`, `relay/web/login.css`, `relay/generate_secrets.py`, `tests/test_relay_integration.py`, `TASKBOARD.md`, `data/relay_totp_qr.png`, `data/relay_login_credentials.txt`, `data/relay_secrets.env` — Fecha: 2026-06-27 20:25



---

## ✅ COMPLETADO

[claude] E+F+G+J+K(01+05) — HA tools (E-01..05 dispatcher unificado ha_control + DANGEROUS + router); web sub-vistas seguridad (F-01..06: pestañas Telegram/Cámaras/Alertas/Eventos/Autonomía/Apps/Aprendizaje con overlay desactivado + CSS); vault web UI (G-01..03: endpoints /api/vault/list+reveal+set+DELETE + UI en Ajustes con reveal TOTP + add/edit); docker update/resources (J-02: op update con cpus/memory); DockerHAService supervisor (J-03); training_store SQLite (K-01+K-05: schema + export QLoRA JSONL); /api/training/stats+export endpoints — 71/71 tests OK — Fecha: 2026-06-30

[claude] DESGLOSE-A..M — 68 tareas granulares marcadas con agente y estado: A..D+B+K → codex; E+F+G+H+J+L+M → claude; I-01 → codex, I-02 → claude. Completados: F-07 (badge CSS ya en SEC-002), H-01 (SecurityPanel GUI en SEC-003), L-01 (system prompt en SEC-010), M-04 (Telegram wiring en SEC-005) — Fecha: 2026-06-30

[claude] SEC-003+SEC-006+SEC-010 — GUI Seguridad escritorio (SecurityPanel + pestaña 🛡️ en MainWindow); categoría Docker en TOOL_CATEGORIES; system prompt del agente con 2 claves Mistral / cámaras / HA / Docker — Archivos: `app/widgets/security_panel.py`, `app/widgets/main_window.py`, `app/tools.py`, `app/ollama_client.py`, `TASKBOARD.md` — Fecha: 2026-06-30

[claude] SEC-001+SEC-002+SEC-005 — Módulo seguridad completo: stubs camera/events/brain_bridge/training_store; SecurityService en supervisor (Telegram heartbeat); notificaciones Telegram automáticas en agent_runner (done>30s/3tools + need_approval); endpoint /api/notify/test; vista Seguridad web (cards: Cámaras/Alertas/Eventos/Autonomía/Docker deshabilitados + Telegram activo con botón Probar) — Archivos: `app/security/camera.py`, `app/security/events.py`, `app/security/brain_bridge.py`, `app/security/training_store.py`, `app/supervisor.py`, `app/api/agent_runner.py`, `app/api/server.py`, `apps/web/index.html`, `apps/web/ui.js`, `apps/web/style.css` — Verificación: 71/71 tests, node --check ui.js/app.js OK — Fecha: 2026-06-30

[codex/claude] MISTRAL-ROUTE-006 — Ruteo Mistral verificado en producción: `_requested_model_from_message()` extrae modelo en relay_connector; `is_mistral_model()` con guardia `":"` evita confusión con tags Ollama locales; `MISTRAL_MODELS` incluye todos los alias cloud. Verificado en revisión `cyberagent-relay-00011-c2p`. — Fecha: 2026-06-30

[codex] LOCAL-WEB-004 — Web local alineada con consola operativa: chats locales, historial por chat, actividad reciente del agente y Markdown también en mensajes de usuario — Archivos: `app/web/index.html`, `app/web/static/app.js`, `app/web/static/style.css`, `tests/test_web_ui_static.py`, `TASKBOARD.md` — Verificación: `node --check` local/relay, `pytest tests/test_web_ui_static.py -q` 4 passed, `pytest -q` 62 passed — Fecha: 2026-06-27 20:18

[codex] WEB-LOGIC-003 — Reconexión fiable PC↔Cloud Run y web más operativa: el relay permite reemplazo seguro de host, el PC reanuncia modelos y audita `/api/status` para reconectar si la revisión activa no lo ve, el header prioriza `active_model`, el relay web añade panel de chats locales, historial por chat, Markdown en usuario/asistente y actividad reciente del agente — Archivos: `relay/main.py`, `app/api/relay_connector.py`, `app/web/static/app.js`, `relay/web/index.html`, `relay/web/app.js`, `relay/web/style.css`, `tests/test_relay_integration.py`, `tests/test_web_ui_static.py`, `TASKBOARD.md` — ⚠️ zona ajena: `app/api/relay_connector.py` por robustez del puente PC↔relay — Verificación: `py_compile`, `node --check`, `pytest -q` 61 passed, Cloud Run revision `cyberagent-relay-00011-c2p` 100% tráfico, asset remoto contiene conversaciones/actividad/modelo activo, `ops_health.ps1 -Detailed` sin warnings, prueba real de redeploy Cloud Run con autoreconexión PC sin reinicio manual y `active_model=richardyoung/qwen3-14b-abliterated:Q5_K_M` — Fecha: 2026-06-27 20:10

[codex] LOGIC-002 — Coherencia de entorno/modelos en reinicios: `restart_windows_instance.ps1` refresca variables de usuario `CYBERAGENT_*`/Mistral antes de arrancar el hijo, sin imprimir secretos; runbook actualizado para cambios de entorno persistido — Archivos: `scripts/restart_windows_instance.ps1`, `docs/OPS_RUNBOOK.md`, `TASKBOARD.md` — Verificación: PowerShell parser OK, dry-run OK, reinicio real OK, `ops_health.ps1 -Detailed` sin warnings, Cloud Run `pc_online:true` con `active_model=richardyoung/qwen3-14b-abliterated:Q5_K_M`, `pytest -q` 57 passed — Fecha: 2026-06-27 19:05

[codex] LOGIC-001 — Improve lógico/usabilidad: `mistral_consult` queda representado en web local, relay Cloud Run y GUI como consulta externa de aprobación por llamada; se oculta “Permitir siempre”, se evita guardar `auto`, se añade nota cloud y test de invariantes de herramienta — Archivos: `app/web/static/app.js`, `app/web/static/style.css`, `relay/web/app.js`, `relay/web/style.css`, `app/widgets/tool_card.py`, `app/widgets/main_window.py`, `tests/test_tool_policy.py` — Verificación: `node --check` local/relay, `py_compile`, `pytest -q` 57 passed, Cloud Run deploy revision `cyberagent-relay-00006-t7x` 100% tráfico, asset remoto contiene `ALWAYS_ASK_TOOLS` — Fecha: 2026-06-27 18:45

[codex] OPS-LOG-001 — Improve logístico/operativo Windows+web: healthcheck con conteo lógico de procesos, detección de duplicados reales, fallback `127.0.0.1`/`localhost`, reinicio controlado dry-run/full/API-only y runbook de operación — Archivos: `scripts/ops_health.ps1`, `scripts/restart_windows_instance.ps1`, `docs/OPS_RUNBOOK.md` — Verificación: PowerShell parser OK, `ops_health.ps1 -Detailed` sin warnings, `restart_windows_instance.ps1 -DryRun -KeepTaskboardListener` OK, `pytest -q` 54 passed — Fecha: 2026-06-27 18:15

[codex] COUNCIL-001 — Consejo multi-modelo local-first implementado: Qwen3-14B abliterated como fast model privado, `cyberagent-original` como power model, Mistral Studio como `mistral_consult` externo con redacción por defecto, aprobación obligatoria por llamada y setup sin guardar API key — Archivos: `app/mistral_client.py`, `app/tools.py`, `app/tool_router.py`, `app/model_router.py`, `scripts/setup_model_council.ps1`, `docs/MODEL_COUNCIL.md`, tests — ⚠️ zona ajena: `app/model_router.py` para corregir ruteo real fast/power al activar Qwen3-14B — Verificación: `pytest -q` 54 passed; `node --check` local/relay; `ollama pull richardyoung/qwen3-14b-abliterated:Q5_K_M` OK — Fecha: 2026-06-27 17:55

[codex] AUDIT-WEBPC-001 — Auditoría/adecuación web+PC excluyendo `ios/`: corregido modo vigilancia local (`this.messages`), saneado HTML generado por Markdown en PWA local/relay, iconos/categoría `council`, permiso GUI `mistral_consult=ask`, endpoints local/relay smokeados y router fast/power corregido para tareas complejas reales — Archivos: `app/web/static/app.js`, `relay/web/app.js`, `app/widgets/main_window.py`, `app/widgets/tool_card.py`, `app/api/agent_runner.py`, `app/ollama_client.py`, `app/model_router.py` — ⚠️ zona ajena: `app/api/agent_runner.py`, `app/ollama_client.py`, `app/model_router.py` por privacidad cloud y ruteo multi-modelo — Verificación: compileall, `pytest -q` 54 passed, TestClient local/relay static/status OK — Fecha: 2026-06-27 17:55

> Mover aquí desde EN PROGRESO al terminar.
> Formato: `[AGENTE] ID — Descripción — Commit: abc1234 — Fecha: YYYY-MM-DD HH:MM`

[claude] WEBPROD-001 — Web como producto único en `apps/web` (relay invisible; fin duplicación) — Commit: dc1449e — Fecha: 2026-06-29
[claude] WEBPROD-002 — Identidad de producto PWA (manifest, sw v12, README) — Commit: 847256f — Fecha: 2026-06-29
[claude] WEBPROD-003 — Modo offline parcial (chats/carpetas/archivos con PC apagado) — Commit: c470b7e — Fecha: 2026-06-29
[claude] WEBPROD-004 — "Modelo local" + footer feedback/escalada reactiva — Commit: 9f45d7f — Fecha: 2026-06-29
[claude] WEBPROD-013+006 — Fix adjuntar imágenes desde la web (el relay las descartaba) + visión local→Pixtral (`app/vision.py`) — Commit: 43ba89b — Fecha: 2026-06-29
[claude] WEBPROD-014 — Adjuntar archivos NO-imagen (`app/attachments.py`, botón clip, drag&drop mixto) — Commit: fdddfdc — Fecha: 2026-06-29
[claude] WEBPROD-011+012 — Adjuntos por conversación + favoritos persistentes (DB+protocolo+tests+UI vista Archivos) — Commit: db7d59a, 686d11a — Fecha: 2026-06-29
[claude] WEBPROD-005 — Crear imágenes (FLUX) desde la web (botón 🎨 → generate_image directo) — Commit: 410f49d — Fecha: 2026-06-29
[claude] WEBPROD-009 — Menú de gasto por mensaje ($ → modal individual + acumulado mensual) — Commit: 8cbefe2 — Fecha: 2026-06-29
[claude] WEBPROD-010 — Subcategorías/proyectos + herencia de contexto padre→hija — Commit: 7e45da4 — Fecha: 2026-06-29
[claude] WEBPROD-007+008 — Compositor móvil pro + gzip/cache en Cloud Run — Commit: 436f0f0 — Fecha: 2026-06-29
[claude] WEBPROD-015 — Suite Google cómoda: conectar/desconectar + acciones rápidas (falta credenciales de Steve) — Commit: 98e80ec — Fecha: 2026-06-29
[claude] WEBPROD-016 — Puente Apps Script (catálogo + exec, tool peligrosa con consentimiento); falta despliegue de Steve — Commit: 303bc07 — Fecha: 2026-06-29

[claude] RELAY-BE-001+002+003 — Relay upgrade backend: modelos passthrough, buffer de sesión 50 msgs + endpoint history, ping/pong PC 15s — Commit: c392367 — Fecha: 2026-06-25
[codex] RELAY-UI-001..005 — Frontend relay remoto: historial remoto/localStorage restaurable, panel de ajustes con modelo/session trust/permisos, badge de cola GPU, watch mode y drag & drop de imágenes — Validación: node --check relay/web/app.js + pytest 47/47 — Commit: 0ba9c1e — Fecha: 2026-06-25 07:45
[codex] TEST-002 — Tests de integración relay mock PC↔relay↔cliente: estado PC offline, modelos, mensaje con modelo/session trust/permisos, aprobación y buffer de historial — Validación: pytest tests 49/49 — Commit: 60d8ce5 — Fecha: 2026-06-25 07:49
[codex] HOTFIX-OLLAMA-001 — Corrige `keep_alive="-1"` incompatible con Ollama nuevo: normaliza `-1`/forever/never a `24h` y añade test de regresión. ⚠️ zona ajena: `app/ollama_client.py` motor Claude por error runtime reportado por Steve — Validación: py_compile + pytest tests 51/51 + probe Ollama `keep_alive=24h` sin error de duración — Commit: 99a0fd3 — Fecha: 2026-06-25 18:18
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

### 🌐 WEB COMO PRODUCTO PRINCIPAL — Desglose de OBJ-WEBPROD (Steve, 2026-06-29)

> Dirigido por Steve por chat → tratado como aprobado (✅). Zona: Claude (web `apps/web/`,
> backend `app/`, relay). Mobile-first. Commit por mejora.

| ID | ✅ | Descripción | Archivos | Estado |
|----|----|-------------|----------|--------|
| WEBPROD-001 | ✅ | Web pasa a producto único en `apps/web` (relay = cable; fin de la duplicación `app/web/static`) | `apps/web/*`, `app/api/server.py`, `relay/main.py`, `relay/deploy.ps1`, `.gitignore` | HECHO `dc1449e` |
| WEBPROD-002 | ✅ | Identidad de producto PWA (manifest id/scope/shortcuts, sw v12 cachea ui.js + fallback navegación, README) | `apps/web/manifest.json`, `apps/web/sw.js`, `apps/web/README.md` | HECHO `847256f` |
| WEBPROD-003 | ✅ | Offline parcial: leer chats/carpetas/archivos con el PC apagado (cache localStorage + fallback) | `apps/web/app.js` | HECHO `c470b7e` |
| WEBPROD-004 | ✅ | "Modelo local" en la UI + footer "¿Es útil?"/"Escalar" con escalera reactiva (prog→Codestral→Large; resto→Medium→Large) | `apps/web/app.js`, `apps/web/style.css` | HECHO `9f45d7f` |
| WEBPROD-005 | ✅ | Mistral creación de imágenes accesible desde la web (botón 🎨 → FLUX directo) | `app/api/relay_connector.py`, `apps/web/*` | HECHO `410f49d` |
| WEBPROD-006 | ✅ | Mistral interpretación de imágenes (visión Pixtral) sobre adjuntos | `app/vision.py`, `app/api/*` | HECHO `43ba89b` (visión local→Pixtral) |
| WEBPROD-007 | ✅ | Web mobile-first "hecha y derecha" (responsive pro, gestos, layout móvil) | `apps/web/style.css` | HECHO `436f0f0` (compositor móvil; resto ya existía) |
| WEBPROD-008 | ✅ | Improve total dentro de límites Cloud Run con coste mínimo (caché, compresión, min-instances) | `relay/main.py` | HECHO `436f0f0` (gzip + cache headers; min-instances=0 ya) |
| WEBPROD-009 | ✅ | Menú de gasto por mensaje: icono $ → modal coste por tokens/€ individual + acumulado mensual de todos los modelos | `apps/web/app.js`, `apps/web/style.css`, `app/api/agent_runner.py`, `app/mistral_usage.py`, `app/local_usage.py` | HECHO `8cbefe2` |
| WEBPROD-010 | ✅ | Carpetas/categorías/proyectos con contexto y modelo por defecto (terminar jerarquía y aplicación de contexto) | `app/database.py`, `app/api/*`, `apps/web/app.js` | HECHO `7e45da4` (subcategorías + herencia de contexto) |
| WEBPROD-011 | ✅ | Adjuntos automáticos por conversación (archivos/links/scripts subidos o generados → archivos de esa conversación) | `app/database.py`, `app/attachments.py`, `app/api/*`, `apps/web/*` | HECHO `db7d59a`+`686d11a` |
| WEBPROD-012 | ✅ | Favoritos: persistir adjuntos aunque se borre la conversación (flag favorite; al borrar conv, conservar favoritos) | `app/database.py`, `app/api/*`, `apps/web/*` | HECHO `db7d59a`+`686d11a` |
| WEBPROD-013 | ✅ | BUG: adjuntar imágenes desde la web no funciona (no envía fotos) | `app/vision.py`, `app/api/relay_connector.py` | HECHO `43ba89b` (relay descartaba las imágenes) |
| WEBPROD-014 | ✅ | Adjuntar archivos NO-imagen (scripts, docs, pdf, csv…) desde la web | `app/attachments.py`, `apps/web/*`, `app/api/*` | HECHO `fdddfdc` |
| WEBPROD-015 | ✅ | Suite Google: implementación cómoda y usable (conexión OAuth fácil + acciones Gmail/Drive/Calendar desde la UI) | `app/google_suite.py`, `app/api/relay_connector.py`, `apps/web/*` | HECHO `98e80ec` (falta que Steve coloque google_credentials.json — ver docs/SETUP_GOOGLE.md) |
| WEBPROD-016 | ✅ | Puente Apps Script: acciones avanzadas arbitrarias en el Workspace (Sheets/Docs/Slides/Gmail/Drive/Calendar; catálogo + `op:exec`), con aprobación como consentimiento | `integrations/apps_script/Code.gs`, `app/apps_script.py`, `app/tools.py`, `app/tool_router.py` | CÓDIGO HECHO `303bc07` — falta que Steve despliegue la webapp y ponga APPS_SCRIPT_URL/SECRET (docs/SETUP_GOOGLE.md) |
| WEBPROD-017 | ✅ | BUG: mensajes duplicados en el chat web (varios sockets procesando cada evento + backend reañadía el turno del usuario al escalar) | `apps/web/app.js`, `app/api/relay_connector.py`, `app/api/server.py` | HECHO `1de52ad` |
| WEBPROD-018 | ✅ | Selector de modelos diferenciado (optgroups Automático/🟢 Local·gratis/☁️ Nube·de pago) + Codestral 22B local cableado (`codestral:22b` → Ollama, `codestral-latest` → Mistral) | `apps/web/app.js`, `app/brain.py` | HECHO `25528b7` |
| WEBPROD-019 | ⏸️ | Conector RunPod: gpt-oss-120b vía vLLM en A100 (start/stop desde la app + auto-apagado por inactividad 10 min). Scaffold listo, sin cablear | `app/runpod.py` | SCAFFOLD `968a8f3` — EN PAUSA (problemas técnicos del modelo, por orden de Steve) |
| WEBPROD-021 | ✅ | BUG: la web móvil "se veía a medias" — Service Worker v12 cache-first sin bump servía mezcla de assets viejos+nuevos. SW→v13 network-first (no-cache, revalida 304); deploys futuros se ven al instante | `apps/web/sw.js` | HECHO `fix SW` |
| WEBPROD-022 | ✅ | Vista móvil refinada: header sobrecargado se recortaba (9 elem. en ~360px) → solo esencial + objetivos táctiles 36px; modal de coste no desborda | `apps/web/style.css` | HECHO |
| WEBPROD-023 | ✅ | BUG: "PC no conectado" tras redeploy — el conector /host se colgaba en cold start de Cloud Run. open_timeout=25 + diagnóstico (relay OK, secretos coinciden; requiere reabrir la app del PC para recargar .env) | `app/api/relay_connector.py` | HECHO `open_timeout` |
| WEBPROD-024 | ✅ | Búsqueda web nivel ChatGPT/Claude: URLs reales (decodifica wrapper DuckDuckGo) + fetch de contenido de top-3 + fuentes numeradas para citar [1][2]. Mantiene Mistral web_search. Gratis | `app/tools.py` | HECHO |
| WEBPROD-026 | ✅ | AUDITORÍA: aprobación de herramientas peligrosas NO funcionaba desde el móvil — el conector no manejaba `approve` → el runner esperaba 60s y cancelaba ("timeout de aprobación"). TODA acción peligrosa fallaba en remoto | `app/api/relay_connector.py` | HECHO |
| WEBPROD-027 | ✅ | AUDITORÍA: el conector no enviaba la lista de modelos al relay → selector móvil vacío. `_send_models()` al conectar (Ollama /api/tags + activo) | `app/api/relay_connector.py` | HECHO |
| WEBPROD-028 | ✅ | Aceptar más instrucciones mientras procesa: cola por sesión (encola y avisa "📥 en cola"; procesa al terminar; descarta history obsoleto) | `app/api/relay_connector.py` | HECHO |
| WEBPROD-029 | ✅ | La web maneja el evento entrante `type:"files"`: refresco en vivo de la pestaña Archivos + badge numérico en la nav si no la estás mirando (hook app.onServerFiles → ui.mergeFiles+renderFiles) | `apps/web/app.js`, `apps/web/ui.js` | HECHO |
| WEBPROD-025 | ✅ | Deploy de apps/scripts del agente por URL pública (estático→túnel principal; dinámico Python/Node→deps+puerto+túnel dedicado) + descargas forzadas /download (PDFs y archivos). Tool `deploy_app` (DANGEROUS) | `app/deployer.py`, `app/tools.py`, `app/tool_router.py`, `app/api/server.py` | HECHO — probado URL pública real |
| WEBPROD-020 | ✅ | BUG: al actualizar y pulsar "Reiniciar" la app se cierra pero no se reabre, y al abrir manualmente vuelve a pedir actualizar sin aplicar cambios. Causa raíz: local va por delante de origin → `updater.py` comparaba HEAD vs sha remoto como cadenas → siempre reportaba update; y `_restart_app` lanzaba la nueva instancia antes de soltar el mutex → se cerraba sola. Fix: check por topología (`fetch`+`rev-list HEAD..origin`) + `relaunch_detached` que espera (`Wait-Process`) a que muera el PID viejo | `app/updater.py`, `main.py` | HECHO `83128ab` |

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

---

# 🛡️ ÉPICO: MÓDULO DE SEGURIDAD (APiComuni v2 dentro de CyberAgent LLM)

> **Dirección de Steve.** NO se fusionan repos: se construye una **v2 del sistema de
> seguridad DENTRO de CyberAgent**, cogiendo lo puntero de `FlEtsv/APiComuni`
> (telegram_centralita, ~8000 LOC) y reescribiéndolo con el estilo cyberllm.
> **Main = CyberAgent LLM. APiComunicaciones pasa a ser `app/security/` (el módulo
> de seguridad de CyberAgent).** El cerebro es nuestro modelo local; la centralita
> son los sentidos/manos. Posible reparto con **Codex** → tareas discretas + zonas.

## ⭐ PROTOCOLO DE PROGRESO (coordinación Claude <-> Codex)
- **Fuente real:** `E:\APiComuni` (USB HA_TRANSFER, con secretos + Docker). NO el clon de GitHub.
- Al **empezar** una tarea, marca su fila: `⭐ progress claude · YYYY-MM-DD HH:MM · NN%`.
  Al **terminar**: `100%`. Así el otro NO la coge si está ⭐ en curso, y vemos el avance.
- **Estilo final = CyberAgent LLM.** El estilo de APiComuni se ELIMINA/adapta.
- **Objetivo:** master (los dos unidos) **funcional** hoy: UI visible (desactivada) +
  Telegram-notif + vault operativos; cámaras/eventos entran desactivados.
- **iOS:** se cablea también la seccion Seguridad en el modulo iOS (lo siguiente a atacar).

## Decisiones de arquitectura (FIJAS)
- **Cerebro:** CyberAgent local (`cyberagent-24b`) dirige todo. La IA externa de
  APiComuni (`ApiAsistente:8082 → /api/ext/chat`) se **reemplaza** por nuestro agente.
- **Cámaras/eventos = Mistral NUBE** (Pixtral) para reacción INSTANTÁNEA (el local
  tiene latencia de carga/swap). El cerebro general sigue local. → split consciente.
- **UI (web + PC):** sección **"Seguridad"** VISIBLE pero **DESACTIVADA** (apartados
  conectados, sin funcionalidad todavía). Solo se ve, no opera.
- **ACTIVO desde ya:** **Telegram como canal de NOTIFICACIÓN** (el MISMO bot del
  proyecto — solo cambia el propósito). Es lo único que se implanta inmediato.
- **Gestor de secretos LOCAL:** 2 claves Mistral (cyberagent + apicomunicaciones) +
  tokens (Telegram, HA, EVENT_TOKEN, dashboard). Revelables en la web tras código
  **authenticator (2FA)**. Reutilizable por todo el sistema.
- **Docker management:** el agente debe poder **levantar/parar/dar recursos/gestionar**
  contenedores (incluido el de HA que ya existe en el Docker local). "Docker = bomba
  → posibilidades infinitas." Tools dedicadas + DANGEROUS_TOOLS.
- **Conciencia del agente:** system prompt debe saber que hay 2 claves Mistral,
  cámaras reales, Home Assistant y Docker local gestionable.
- **QLoRA:** más adelante. El MVP solo debe **dejar el grifo de datos abierto**
  (instrumentar decisiones/feedback para el futuro entrenamiento en RunPod).

## Lo PUNTERO de APiComuni a portar (con estilo cyberllm)
| Módulo origen | Función | Destino (estado) |
|---|---|---|
| `telegram_bot.py` (3187 LOC) | Bot, 2FA, viewers, chat IA, notif, teclados cámara | `app/security/telegram/` — **notif ACTIVA**, resto desactivado |
| `motion_tracker.py` (1417) | Loop de cámara, snapshots, seguimiento | `app/security/motion.py` — desactivado |
| `event_handler.py` + `event_store.py` | Orquestador de eventos + ring buffer | `app/security/events.py` — desactivado |
| `camera_client.py` | RTSP / snapshot HA / clip ffmpeg | `app/security/camera.py` — desactivado |
| `ai_client.py` | **SWAP** → llama a nuestro agente/Mistral nube | `app/security/brain_bridge.py` |
| `autonomy.py` | Política manual/operativa/alto-impacto | mapea a nuestro sistema de **aprobaciones** |
| `action_executor.py` | Ejecuta acciones (HA: luz/alarma/TTS) | `app/security/actions.py` — desactivado |
| `dashboard_router.py` + templates | alertas/events/apps/learning | vista web **Seguridad** (apartados, desactivados) |
| `app_registry.py`, `feedback_store.py`, `property_context.py` | apps, feedback, contexto propiedad | portar; feedback → training_store |
| `docker-compose.yml` (centralita) | contenedor | el agente lo gestiona vía tools Docker |

## TAREAS (zonas + estado · para reparto con Codex)

| ID | Estado | Zona | Descripción | Archivos |
|----|----|----|-------------|----------|
| SEC-001 | ✅ 100% claude | claude | Estructura `app/security/` (esqueleto de módulos, todo no-op/flag SECURITY_ENABLED=False) + arranque opcional bajo el supervisor (6º servicio, apagado por defecto) | `app/security/__init__.py`, `app/supervisor.py` |
| SEC-002 | ✅ 100% claude | claude | Vista **Seguridad** en la web (móvil): nav-item + `view-security` con sub-apartados (Cámaras · Eventos · Alertas · Autonomía · Apps) VISIBLES pero deshabilitados (badge "próximamente") | `apps/web/index.html`, `apps/web/app.js`, `apps/web/ui.js`, `apps/web/style.css` |
| SEC-003 | ✅ 100% claude | claude | Sección **Seguridad** en la GUI de escritorio (PC), misma estructura, desactivada | `app/widgets/security_panel.py`, `app/widgets/main_window.py` |
| SEC-004 | ✅ 100% claude | claude | **Gestor de secretos LOCAL** (`app/secrets_vault.py`): cifra/guarda claves (2× Mistral, Telegram, HA, EVENT_TOKEN); revela en la web tras 2FA TOTP. Endpoint + UI en Ajustes | `app/secrets_vault.py`, `app/api/server.py`, `apps/web/*` |
| SEC-005 | ✅ 100% claude | claude | **Telegram NOTIFICACIONES (ACTIVO)**: portar el bot del proyecto; CyberAgent emite por Telegram (tarea hecha, aprobación pendiente, alerta). Reusa TELEGRAM_BOT_TOKEN/CHAT_ID del vault | `app/security/notify.py`, `app/api/agent_runner.py`, `app/api/server.py` |
| SEC-006 | ✅ 100% claude | claude | **Tools Docker** para el agente: `docker_ps/start/stop/restart/logs/stats/compose_up/compose_down/run`. En DANGEROUS_TOOLS. Categoría router "docker" | `app/tools.py`, `app/tool_router.py`, `app/docker_tools.py` |
| SEC-007 | ⬜ | * | **brain_bridge** + endpoint `/api/ext/chat` (compatible ApiAsistente) que corre nuestro agente; análisis de cámara → Mistral NUBE (Pixtral) | `app/security/brain_bridge.py`, `app/api/server.py` |
| SEC-008 | ⬜ | * | Portar `camera_client` + `motion_tracker` (DESACTIVADO; solo estructura + config) | `app/security/camera.py`, `app/security/motion.py` |
| SEC-009 | ⬜ | * | Portar `event_handler`+`event_store`+`action_executor`+`autonomy` (DESACTIVADO); autonomía → mapear a aprobaciones | `app/security/events.py`, `actions.py` |
| SEC-010 | ✅ 100% claude | claude | **Conciencia del agente**: system prompt + tools docs reflejan 2 claves Mistral, cámaras, HA, Docker | `app/ollama_client.py` |
| SEC-012 | ⬜ | * | Cablear seccion **Seguridad** en el modulo **iOS** (vista + theme cyberagent), desactivada | `ios/CyberAgent/*` |
| SEC-011 | ⬜ | * | **training_store** (grifo de datos QLoRA): captura decisión→resultado, feedback 👍/👎, aprobaciones, en formato instrucción/respuesta/señal | `app/training_store.py` |

> **Reglas de reparto:** Claude toma SEC-001..005 (estructura + UI + secretos +
> Telegram). Codex puede tomar SEC-006..011 (tools Docker, brain_bridge, portado de
> módulos, training_store). Commit por tarea con `[claude]`/`[codex] tipo: desc`.
> NADA se activa salvo Telegram-notif y el vault; el resto entra DESACTIVADO.

## Lo que NO se rompe
Agente, relay/móvil, modos (Claude/código/imagen), supervisor, persistencia, las 120
tools actuales. El módulo de seguridad se acopla, gateado por `SECURITY_ENABLED`.

---

## 🧱 DESGLOSE GRANULAR (cola larga · Claude + Codex) — integrar 2 sistemas
> Marca con estrella al empezar (`* progress QUIEN · fecha hora · NN%`), 100% al terminar.
> Todo DESACTIVADO (gateado por `SECURITY_ENABLED`) salvo lo marcado [ACTIVO].
> Estilo CyberAgent. Secretos SIEMPRE vía `app.secrets_vault` (prefijo `SEC_`).

### A · Cerebro / brain_bridge (la IA de la centralita = nuestro agente)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| A-01 | ⬜ | codex | Endpoint `/api/ext/chat` compatible con el formato ApiAsistente (request/response idénticos) | `app/api/server.py` |
| A-02 | ⬜ | codex | Mapear sesión ApiAsistente a conversación CyberAgent (session_id) | `app/security/brain_bridge.py` |
| A-03 | ⬜ | codex | Ruta de VISIÓN de cámara a Mistral NUBE (Pixtral, `SEC_MISTRAL_*`) para reacción instantánea | `app/security/brain_bridge.py`, `app/vision.py` |
| A-04 | ⬜ | codex | Ruta de CHAT (Telegram a agente) al modelo local cyberagent-24b con tools | `app/security/brain_bridge.py` |
| A-05 | ⬜ | codex | Cliente Mistral con la 2a clave + rate-limit separado del de CyberAgent | `app/security/mistral_sec.py` |
| A-06 | ⬜ | codex | Prompts de evento/visual (portar `_build_event_prompt`/`_build_visual_prompt`) | `app/security/prompts.py` |
| A-07 | ⬜ | codex | Parser de decisión (accion/confianza/motivo) | `app/security/decision.py` |
| A-08 | ⬜ | codex | Tests del brain_bridge (mock Mistral + local) | `tests/test_brain_bridge.py` |

### B · Telegram completo (más allá de notif [ya ACTIVO])
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| B-01 | ⬜ | codex | Bot con polling (python-telegram-bot) bajo el supervisor, gateado | `app/security/telegram/bot.py` |
| B-02 | ⬜ | codex | Comandos `/start /help /status /pending` | `app/security/telegram/commands.py` |
| B-03 | ⬜ | codex | 2FA / auth (admin + viewers) reutilizando TOTP del vault | `app/security/telegram/auth.py` |
| B-04 | ⬜ | codex | viewer_store (registro dinámico de viewers) | `app/security/telegram/viewers.py` |
| B-05 | ⬜ | codex | Chat-con-el-agente desde Telegram (chat_session a brain_bridge) | `app/security/telegram/chat.py` |
| B-06 | ⬜ | codex | Teclados inline (confirmar acción / ver cámara) | `app/security/telegram/keyboards.py` |
| B-07 | ⬜ | codex | Sanitizado HTML Telegram (quitar think, markdown a HTML) | `app/security/telegram/format.py` |
| B-08 | ⬜ | codex | Notif a chat principal + extras + viewers | `app/security/telegram/notify.py` |
| B-09 | ⬜ | codex | Comando activar/desactivar autonomía en caliente | `app/security/telegram/commands.py` |

### C · Cámaras + motion
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| C-01 | ⬜ | codex | camera_client: snapshot vía HA | `app/security/camera.py` |
| C-02 | ⬜ | codex | camera_client: RTSP frame con ffmpeg | `app/security/camera.py` |
| C-03 | ⬜ | codex | camera_client: clip corto (ffmpeg) | `app/security/camera.py` |
| C-04 | ⬜ | codex | motion_tracker: loop de seguimiento (snapshots cada N s) | `app/security/motion.py` |
| C-05 | ⬜ | codex | Cooldown + duración máx | `app/security/motion.py` |
| C-06 | ⬜ | codex | Notif inteligente durante seguimiento (followup snapshots) | `app/security/motion.py` |
| C-07 | ⬜ | codex | Registro de cámaras (property.json a DB) | `app/security/property_context.py` |

### D · Eventos + autonomía + acciones
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| D-01 | ⬜ | codex | event_store ring-buffer (portar) | `app/security/events.py` |
| D-02 | ⬜ | codex | event_handler: normaliza a CameraEvent/IncomingEvent | `app/security/events.py` |
| D-03 | ⬜ | codex | Routers `/security/events/*` `/security/cameras/*` montados en :8765 | `app/api/security_routes.py` |
| D-04 | ⬜ | codex | Auth apps externas (X-Event-Token = SEC_EVENT_TOKEN) | `app/api/security_routes.py` |
| D-05 | ⬜ | codex | autonomy: manual/operativa/alto-impacto a aprobaciones de CyberAgent | `app/security/autonomy.py` |
| D-06 | ⬜ | codex | action_executor: ejecutar decisión (timeout confirmación) | `app/security/actions.py` |
| D-07 | ⬜ | codex | app_registry (apps externas) | `app/security/app_registry.py` |
| D-08 | ⬜ | codex | alert_history + feedback_store (mas/menos) a training_store | `app/security/feedback.py` |
| D-09 | ⬜ | codex | schedule_store (tareas programadas de seguridad) | `app/security/schedule.py` |

### E · Home Assistant (cada acción = tool del agente)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| E-01 | ✅ | claude | Tool `ha_control` (luz IR on/off, autofoco on/off) | `app/security/ha_tools.py` |
| E-02 | ✅ | claude | Tool `ha_speak` (TTS por altavoz) | `app/security/ha_tools.py` |
| E-03 | ✅ | claude | Tool `ha_camera` (snapshot/stream) | `app/security/ha_tools.py` |
| E-04 | ✅ | claude | Tool `ha_script` (reboot, sync_clock, genérico) | `app/security/ha_tools.py` |
| E-05 | ✅ | claude | Registrar tools HA en tools.py + router + DANGEROUS | `app/tools.py`, `app/tool_router.py` |

### F · UI Web Seguridad (cada sub-vista, desactivada)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| F-01 | ✅ | claude | Sub-vista Cámaras (grid + placeholder) | `apps/web/index.html`, `apps/web/style.css` |
| F-02 | ✅ | claude | Sub-vista Eventos (timeline) | `apps/web/index.html`, `apps/web/style.css` |
| F-03 | ✅ | claude | Sub-vista Alertas (historial + feedback) | `apps/web/index.html`, `apps/web/style.css` |
| F-04 | ✅ | claude | Sub-vista Autonomía (toggle modos) | `apps/web/index.html`, `apps/web/style.css` |
| F-05 | ✅ | claude | Sub-vista Apps (registro externas) | `apps/web/index.html`, `apps/web/style.css` |
| F-06 | ✅ | claude | Sub-vista Aprendizaje (training_store stats) | `apps/web/index.html`, `apps/web/ui.js` |
| F-07 | ✅ | claude | Badge "próximamente" consistente | `apps/web/style.css` |

### G · Vault web UI + 2FA
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| G-01 | ✅ | claude | Endpoint `/api/vault/list` (enmascarado) + `/api/vault/reveal` (TOTP) | `app/api/server.py` |
| G-02 | ✅ | claude | UI en Ajustes: lista de secretos + input authenticator a revelar | `apps/web/index.html`, `apps/web/ui.js`, `apps/web/style.css` |
| G-03 | ✅ | claude | UI: añadir/editar/borrar secreto | `apps/web/index.html`, `apps/web/ui.js` |
| G-04 | ⬜ | claude | Vault por el conector del relay (móvil) | `app/api/relay_connector.py` |

### H · UI PC (GUI escritorio)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| H-01 | ✅ | claude | Sección Seguridad en la GUI, desactivada | `app/widgets/security_panel.py`, `app/widgets/main_window.py` |
| H-02 | ⬜ | claude | Indicador de estado del módulo en el tray | `main.py` |

### I · iOS (lo siguiente a atacar)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| I-01 | ⬜ | codex | Vista Seguridad (SwiftUI) theme cyberagent, desactivada | `ios/CyberAgent/Security/SecurityView.swift` |
| I-02 | ⬜ | claude | Cliente de notificaciones push (recibir alertas) | `ios/CyberAgent/Security/PushManager.swift` |

### J · Docker (más granular)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| J-01 | ⬜ | claude | Compose del stack de seguridad (HA/comunicaciones) gestionable por el agente | `integrations/security/docker-compose.yml` |
| J-02 | ✅ | claude | Tool docker op update/resources (límites cpu/mem) | `app/docker_tools.py` |
| J-03 | ✅ | claude | Health/auto-arranque del contenedor HA bajo el supervisor (gateado) | `app/supervisor.py` |

### K · training_store + QLoRA
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| K-01 | ✅ | claude | Esquema training_store (instrucción/respuesta/señal) | `app/training_store.py` |
| K-02 | ✅ | claude | Hook: capturar decisión a resultado de eventos | `app/security/events.py` |
| K-03 | ✅ | claude | Hook: capturar feedback mas/menos | `app/security/feedback.py` |
| K-04 | ✅ | claude | Hook: capturar aprobaciones/rechazos del agente | `app/api/agent_runner.py` |
| K-05 | ✅ | claude | Export a formato QLoRA (jsonl chat) | `app/training_store.py` |
| K-06 | ⬜ | claude | Pipeline de entrenamiento en RunPod (script + doc) | `integrations/training/runpod_qlora.md` |

### L · Conciencia del agente
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| L-01 | ✅ | claude | System prompt: 2 claves Mistral, cámaras, HA, Docker, módulo seguridad | `app/ollama_client.py` |
| L-02 | ⬜ | claude | Doc de tools nuevas clara para el modelo | schemas en `app/ollama_client.py` |

### M · Limpieza / estilo + tests + docs + wiring
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| M-01 | ⬜ | claude | Adaptar nombres/estilo APiComuni a cyberllm | `app/security/*` |
| M-02 | ⬜ | claude | Tests por módulo de seguridad | `tests/test_security_*.py` |
| M-03 | ⬜ | claude | Doc docs/SECURITY_MODULE.md (arquitectura final) | `docs/` |
| M-04 | ✅ | claude | Wiring notif: tarea-hecha / aprobación-pendiente a Telegram [ACTIVO] | `app/api/agent_runner.py` |

---

## 📹 DESGLOSE GRANULAR — DASHBOARD DE CÁMARAS + IA DE VIGILANCIA (visión de Steve)
> Ingeniería jefe Steve + Claude. Marca estrella al empezar. Todo en módulo seguridad
> (gateado SECURITY_ENABLED), estilo CyberAgent. Modelo visión: ver grupo T.
> Objetivo: mantener a salvo la casa y los gatos, con trabajo IMPECABLE (es seguridad).

### N · Dashboard de Cámaras (rejilla principal)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| N-01 | ✅ | claude | Layout dashboard de cámaras (grid responsive, web + PC) | `apps/web/*`, `app/widgets/*` |
| N-02 | ⬜ | claude | Tarjeta de cámara con stream EN TIEMPO REAL (HA camera_proxy / RTSP a WebRTC-HLS-MJPEG) | `apps/web/*`, `app/security/stream.py` |
| N-03 | ✅ | claude | Botón "Añadir cámara" (modal: nombre, tipo exterior/interior, RTSP/HA entity, ubicación) | `apps/web/*` |
| N-04 | ✅ | claude | Botón "Volver a CyberAgent" | `apps/web/*` |
| N-05 | ✅ | claude | Botón "Abrir agente con contexto de cámara" (seleccionar cámara a chat contextualizado) | `apps/web/*`, `app/api/*` |
| N-06 | ✅ | claude | Estado por cámara (online/offline, IA activa, última detección) | `apps/web/*` |
| N-07 | ✅ | claude | Backend: CRUD de cámaras en DB (tipo, fuente, ubicación, zonas, tools asignadas) | `app/security/cameras_db.py` |
| N-08 | ✅ | claude | Backend: proxy de stream en vivo (go2rtc o ffmpeg RTSP a WebRTC) | `app/security/stream.py` |

### O · Vista de cámara individual (IA en vivo)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| O-01 | ⬜ | claude | Layout vista de UNA cámara (video grande + panel IA) | `apps/web/*` |
| O-02 | ⬜ | claude | Panel "Lo que la IA ve y razona" EN VIVO (stream de razonamiento) | `apps/web/*`, `app/security/live_brain.py` |
| O-03 | ⬜ | claude | Lista de DETECCIONES (timestamp, tipo, confianza, recorte) | `apps/web/*` |
| O-04 | ⬜ | claude | ACTIVIDADES IGNORADAS (lo que la IA descartó) + por qué | `apps/web/*` |
| O-05 | ⬜ | claude | Línea de tiempo de eventos de esa cámara | `apps/web/*` |
| O-06 | ⬜ | claude | Backend: stream del razonamiento IA por cámara (SSE/WS) | `app/security/live_brain.py` |

### P · Grabación / reproducción / exportación
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| P-01 | ⬜ | claude | Grabar clip (manual + automático en evento) | `app/security/recorder.py` |
| P-02 | ⬜ | claude | Almacén de videos por cámara (DB índice + ficheros) | `app/security/recorder.py` |
| P-03 | ⬜ | claude | Reproductor con controles nativos (play/pause/seek/velocidad) | `apps/web/*` |
| P-04 | ⬜ | claude | Saltar a MOMENTOS de actividad (marcadores en la timeline) | `apps/web/*` |
| P-05 | ⬜ | claude | Recorte de video (trim in/out) | `apps/web/*`, `app/security/recorder.py` |
| P-06 | ⬜ | claude | Descarga / exportación de clips | `app/api/*` |
| P-07 | ⬜ | claude | Exportar el RAZONAMIENTO de la IA (por qué fue amenaza, si notificó, si lo descartó) en informe | `app/security/report.py` |
| P-08 | ⬜ | claude | Retención/limpieza de grabaciones (política + espacio) | `app/security/recorder.py` |

### Q · Zonas de vigilancia (áreas dibujables)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| Q-01 | ⬜ | claude | Editor de zonas sobre el frame (dibujar polígonos) | `apps/web/*` |
| Q-02 | ⬜ | claude | Tipos de zona: WARNING/amenaza y SEGURA (colorear cada una) | `apps/web/*` |
| Q-03 | ⬜ | claude | Solapamiento: prevalece la de MAYOR riesgo | `app/security/zones.py` |
| Q-04 | ⬜ | claude | Solo notificar si la amenaza está DENTRO de zona de vigilancia | `app/security/zones.py` |
| Q-05 | ⬜ | claude | Cuadrícula "lo que la IA debe vigilar" (regiones de interés) | `apps/web/*` |
| Q-06 | ⬜ | claude | Backend: persistir zonas por cámara + punto-en-polígono | `app/security/zones.py` |
| Q-07 | ⬜ | claude | La IA recibe las zonas como contexto al analizar | `app/security/live_brain.py` |

### R · Cámara EXTERIOR
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| R-01 | ⬜ | claude | Tipo exterior (config + eventos esperados: intrusión, merodeo, persona) | `app/security/camera_types.py` |
| R-02 | ⬜ | claude | Análisis de personas: etnia, vestimenta, acción, aspecto, puntos clave (descripción policial) | `app/security/analysis_exterior.py` |
| R-03 | ⬜ | claude | Mejora de imagen (resolución/nitidez/enfoque) para capturar lo importante | `app/security/imaging.py` |
| R-04 | ⬜ | claude | Lógica de DISUASIÓN (la IA decide disuadir vs alertar) | `app/security/deterrence.py` |
| R-05 | ⬜ | claude | Tools de disuasión exterior (HA + externos): luz potente/láser/linterna BT, altavoz con retransmisión de video en curso | `app/security/deterrence_tools.py` |
| R-06 | ⬜ | claude | Contexto de la cámara (ubicación, qué vigilar) editable | `apps/web/*`, `cameras_db` |
| R-07 | ⬜ | claude | Catálogo de herramientas disuasorias asignables por cámara | `apps/web/*`, `app/security/*` |
| R-08 | ⬜ | claude | Escalado de amenaza (disuadir a alertar usuario a emergencia) | `app/security/deterrence.py` |

### S · Cámara INTERIOR (protección de gatos)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| S-01 | ⬜ | claude | Tipo interior (hereda genérico, NO exterior) | `app/security/camera_types.py` |
| S-02 | ⬜ | claude | Gestión de mascotas (añadir gato + fotos para reconocimiento) | `apps/web/*`, `app/security/pets.py` |
| S-03 | ⬜ | claude | Reconocimiento/re-identificación de gatos por las fotos | `app/security/pets.py` |
| S-04 | ⬜ | claude | Modo trayectoria (seguir el recorrido del gato) | `app/security/motion.py` |
| S-05 | ⬜ | claude | Zonas peligrosas para el animal (cocina, enchufes, TV…) dibujables | `apps/web/*`, `zones` |
| S-06 | ⬜ | claude | Detección de peligros (gato en zona peligrosa, rotura, desorden, anomalía) | `app/security/analysis_interior.py` |
| S-07 | ⬜ | claude | Aprendizaje de lugares seguros/patrones de los gatos | `app/security/pets.py`, `training_store` |
| S-08 | ⬜ | claude | Tools de disuasión interior (altavoz potente, sonidos por escenario para separar gatos) | `app/security/deterrence_tools.py` |
| S-09 | ⬜ | claude | Modo noche (conectar a dispositivos de disuasión interior — próximamente) | `app/security/deterrence_tools.py` |
| S-10 | ⬜ | claude | Preconfigurar 3 cámaras de interior | `cameras_db` |

### T · Modelo de visión local rápido (+ nube)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| T-01 | ⬜ | claude | Evaluar VLM local ligero/rápido (Moondream2 ~1.8B vs Qwen2.5-VL 3B) para triage continuo | `docs/VISION_MODEL.md` |
| T-02 | ⬜ | claude | Integrar el VLM de triage (presencia/movimiento/¿persona o gato?) en Ollama | `app/security/vision_local.py` |
| T-03 | ⬜ | claude | Análisis profundo bajo demanda a Mistral NUBE (Pixtral) cuando el triage dispara | `app/security/brain_bridge.py` |
| T-04 | ⬜ | claude | Pipeline eficiente (frame sampling, no cada frame; cola; backpressure) | `app/security/vision_pipeline.py` |

### U · Comunicaciones/Notificaciones CENTRALIZADAS (CyberAgent general, NO submódulo)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| U-01 | ✅ | claude | Módulo `app/comms/` central (Telegram canal); seguridad solo lo USA | `app/comms/__init__.py`, `app/comms/telegram.py` |
| U-02 | ✅ | claude | Fuentes unificadas: respuestas de agentes, ERRORES del sistema, amenazas ext/int | `app/comms/router.py` |
| U-03 | ✅ | claude | Niveles de IMPORTANCIA + filtros de mensajes | `app/comms/router.py` |
| U-04 | ✅ | claude | (futuro) múltiples chats/canales por tipo; de momento un solo chat | `app/comms/*` |
| U-05 | ✅ | claude | Comandos del módulo de comunicación (config, silenciar, filtrar) | `app/comms/commands.py` |
| U-06 | ⬜ | claude | Plan de presentación de mensajes (formato por tipo/importancia) | `docs/COMMS_PLAN.md` |

---

## ⚖️ V · COORDINACIÓN DE VRAM/GPU (usuario vs seguridad) — 16 GB compartidos
> Estrategia: vigilancia continua en CPU (0 VRAM); GPU/nube solo con movimiento;
> usuario tiene prioridad de GPU, seguridad cae a NUBE cuando la GPU está ocupada.
> Así la seguridad NUNCA bloquea al usuario y el usuario NUNCA ciega la seguridad.

| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| V-01 | ✅ | claude | Capa 0: detección de MOVIMIENTO en CPU (OpenCV/ffmpeg) por cámara, sin GPU | `app/security/motion_cpu.py` |
| V-02 | ✅ | claude | Árbitro de GPU (broker): estado "GPU ocupada por usuario" consultable; seguridad lo respeta | `app/security/gpu_broker.py` |
| V-03 | ✅ | claude | Router de visión: GPU libre→VLM local; GPU ocupada→Pixtral nube; amenaza→siempre nube | `app/security/vision_router.py` |
| V-04 | ✅ | claude | Prioridad: la inferencia del usuario NUNCA espera por seguridad (seguridad degrada a nube) | `app/security/gpu_broker.py`, `app/ollama_client.py` |
| V-05 | ⬜ | claude | Co-residencia: cerbero 24B Q3 (~11GB) + VLM triage (~2.5GB) caben juntos; validar VRAM real | `docs/VISION_MODEL.md` |
| V-06 | ✅ | claude | Backpressure/cola: si llegan muchos frames con movimiento, descartar/encolar sin saturar | `app/security/vision_pipeline.py` |
| V-07 | ⬜ | claude | Métricas: cuánto se usó CPU vs GPU vs nube (coste/latencia) en el dashboard | `apps/web/*`, `app/security/*` |
| V-08 | ✅ | claude | Modo "no molestar visión local" cuando el usuario está en tarea pesada (juego/render) | `app/security/gpu_broker.py` |

---

## 🧠 ECOSISTEMA DE ENTRENAMIENTO + ALMACENAMIENTO + CÓMPUTO (visión de Steve)
> Ecosistema VIVO: el feedback de uso entrena los modelos LOCALES más usados y
> críticos. Entrenar SOLO con el usuario presente en el PC (necesita VRAM y deja
> la casa sin vigilancia local → se degrada a nube). SD 1.8 TB, RAM 64 GB, CPU
> con núcleos de sobra → aprovecharlos. Solo añadir tareas (compañeros activos).

### W · Feedback → Datos de entrenamiento (recolección + señales)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| W-01 | ✅ | claude | Capturar feedback "¿es útil?" (mas/menos) de cada respuesta → training_store con la señal | `app/training_store.py`, `apps/web/*` |
| W-02 | ✅ | claude | Capturar feedback "¿el RAZONAMIENTO es correcto?" (separado de la respuesta) | `apps/web/*`, `app/training_store.py` |
| W-03 | ✅ | claude | Etiquetar QUÉ MODELO generó cada respuesta (para entrenar al correcto) | `app/api/agent_runner.py` |
| W-04 | ✅ | claude | Capturar aprobaciones/rechazos de tools como señal de preferencia | `app/api/agent_runner.py` |
| W-05 | ✅ | claude | Capturar CORRECCIONES del usuario (reescribe/corrige) → par instrucción→buena-respuesta | `app/training_store.py` |
| W-06 | ✅ | claude | Feedback de seguridad (detección amenaza correcta? falso pos/neg) → dataset del modelo de visión | `app/security/feedback.py` |
| W-07 | ✅ | claude | Normalizar todo a formato entrenamiento (chat jsonl con peso/señal) | `app/training_store.py` |
| W-08 | ✅ | claude | UI: botones de feedback de razonamiento (correcto/incorrecto) en cada respuesta | `apps/web/*` |

### X · Auto-entrenamiento por modelo (umbral, scheduling, QLoRA)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| X-01 | ⬜ | claude | Registro de modelos ENTRENABLES (los más usados + críticos + LOCALES) con metadatos (uso, criticidad) | `app/training/registry.py` |
| X-02 | ⬜ | claude | Contador de ejemplos de entrenamiento POR MODELO (cuántos de alta señal hay listos) | `app/training/registry.py` |
| X-03 | ⬜ | claude | **Detección del UMBRAL por modelo** (24B ~1500, Codestral ~1000, visión ~500; auto-sugerido + configurable) | `app/training/thresholds.py` |
| X-04 | ⬜ | claude | Cola de entrenamiento (qué modelo toca cuando alcanza umbral) | `app/training/queue.py` |
| X-05 | ⬜ | claude | Scheduler: entrenar SOLO con el usuario PRESENTE en el PC (detección de presencia/actividad) | `app/training/scheduler.py` |
| X-06 | ⬜ | claude | Coordinar con seguridad: al entrenar, avisar y degradar vigilancia local a NUBE (casa no queda ciega) | `app/training/scheduler.py`, `app/security/gpu_broker.py` |
| X-07 | ⬜ | claude | Pipeline QLoRA: local si cabe en 16 GB, si no RunPod A100 (decidir por VRAM/tamaño) | `app/training/qlora.py` |
| X-08 | ⬜ | claude | Evaluación post-entrenamiento (A/B contra el anterior) antes de promover el adapter | `app/training/evaluate.py` |
| X-09 | ⬜ | claude | Versionado de modelos/adapters + rollback si empeora | `app/training/versioning.py` |
| X-10 | ⬜ | claude | Notificar (comms/Telegram) cuando un modelo está listo para entrenar / terminó / mejoró | `app/comms/*` |
| X-11 | ⬜ | claude | Consentimiento: el entrenamiento lo lanza el usuario (no automático sin permiso) | `apps/web/*`, `app/widgets/*` |

### Y · Almacenamiento (SD 1.8 TB: modelos, datasets, video 15 días por ley)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| Y-01 | ⬜ | claude | Estructura en la SD: /models /datasets /videos /backups, con config de ruta base | `app/storage/layout.py` |
| Y-02 | ⬜ | claude | Mover/configurar modelos de Ollama a la SD (espacio) sin romper inferencia | `docs/STORAGE.md` |
| Y-03 | ⬜ | claude | Almacén de VIDEO por cámara eficiente (H.265, segmentos cortos, índice) | `app/security/recorder.py` |
| Y-04 | ⬜ | claude | **Retención LEGAL 15 días** del video (auto-borrado de lo más viejo) | `app/storage/retention.py` |
| Y-05 | ⬜ | claude | Gestión de ESPACIO (cuota por categoría, alertas si se llena, limpieza) | `app/storage/quota.py` |
| Y-06 | ⬜ | claude | Almacén de datasets de entrenamiento (jsonl comprimido, por modelo, versionado) | `app/storage/datasets.py` |
| Y-07 | ⬜ | claude | Índice/DB de grabaciones (cámara, momento, eventos asociados) | `app/security/recorder.py` |
| Y-08 | ⬜ | claude | Backups del vault/DB en la SD (rotación) | `app/storage/backup.py` |

### Z · Cómputo CPU/RAM (64 GB RAM + núcleos de sobra)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| Z-01 | ✅ | claude | Perfil de recursos (RAM 64 GB, N núcleos) + presupuesto por subsistema | `app/compute/profile.py` |
| Z-02 | ✅ | claude | Cargas en CPU: movimiento (OpenCV), transcripción (whisper.cpp), embeddings RAG | `app/compute/cpu_pool.py` |
| Z-03 | ✅ | claude | Mover lo NO urgente a CPU/RAM cuando la GPU está ocupada (batch, embeddings) | `app/compute/scheduler.py` |
| Z-04 | ✅ | claude | Caché en RAM de frames/embeddings (aprovechar los 64 GB) | `app/compute/ram_cache.py` |
| Z-05 | ✅ | claude | Pool de workers CPU para visión/audio de respaldo | `app/compute/cpu_pool.py` |
| Z-06 | ✅ | claude | VLM tiny en CPU como último recurso si GPU+nube no disponibles | `app/security/vision_local.py` |

### AA · Modo JUEGO / minimización de recursos
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| AA-01 | ✅ | claude | Detectar "modo juego" (fullscreen / GPU intensiva) y entrar en modo mínimo | `app/compute/game_mode.py` |
| AA-02 | ✅ | claude | Liberar el 24B de VRAM (free_vram) al entrar en juego | `app/compute/game_mode.py` |
| AA-03 | ✅ | claude | Seguridad en juego: solo ojo local mínimo o degradar a nube/CPU | `app/security/gpu_broker.py` |
| AA-04 | ✅ | claude | Si no cabe nada local → Mistral NUBE para todo lo crítico | `app/security/vision_router.py` |
| AA-05 | ✅ | claude | Restaurar al salir del juego (recargar modelos, reanudar vigilancia local) | `app/compute/game_mode.py` |
| AA-06 | ✅ | claude | Pausar entrenamiento si arranca un juego (libera VRAM) | `app/training/scheduler.py` |

---

## 🎛️ SUBSISTEMA DE ENTRENAMIENTO — menú + pipeline por modelo (visión de Steve)
> Al llegar el umbral: avisar por TODOS los medios. Menú en Ajustes: elegir modelo
> y "Entrenar". Cada modelo tiene su FICHA con datos/umbral/destino/versiones.
> Solo añadir tareas (compañeros activos). Estilo CyberAgent.

### AB · Ficha de modelo entrenable (el "detrás" por modelo)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| AB-01 | ✅ | claude | Esquema "ModelCard" entrenable: id, base, cuantización-train, destino(local/runpod), umbral, plantilla prompt, criticidad, uso | `app/training/model_card.py` |
| AB-02 | ✅ | claude | Registrar las fichas: cyberagent-24b, codestral, visión-seguridad, router-tools | `app/training/registry.py` |
| AB-03 | ✅ | claude | Mapear QUÉ datos entrenan cada modelo (fuente→modelo): chats→24b, code_specialist→codestral, detecciones→visión, tool_router→router | `app/training/data_map.py` |
| AB-04 | ✅ | claude | Hiperparámetros QLoRA por modelo (rank, alpha, lr, epochs, batch) con defaults sensatos | `app/training/hparams.py` |
| AB-05 | ✅ | claude | Estimador de recursos/tiempo por modelo (VRAM train, horas RunPod, coste $) | `app/training/estimate.py` |

### AC · Dataset por modelo (preparación + curación)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| AC-01 | ✅ | claude | Builder de dataset por modelo desde training_store (filtra por señal mínima) | `app/training/dataset_builder.py` |
| AC-02 | ✅ | claude | Dedup + balanceo (no sobre-representar un tipo de ejemplo) | `app/training/dataset_builder.py` |
| AC-03 | ⬜ | claude | Editor/revisor de dataset en la UI: ver, excluir, etiquetar ejemplos antes de entrenar | `apps/web/*` |
| AC-04 | ✅ | claude | Split train/eval (holdout para la evaluación A/B) | `app/training/dataset_builder.py` |
| AC-05 | ⬜ | claude | Export a jsonl chat (formato del entrenador) comprimido, versionado en la SD | `app/storage/datasets.py` |
| AC-06 | ✅ | claude | Anonimizar/limpiar PII sensible antes de entrenar | `app/training/sanitize.py` |

### AD · Umbral + aviso multicanal
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| AD-01 | ✅ | claude | Watcher de umbral por modelo (cuenta alta señal vs threshold; estado "listo") | `app/training/threshold_watcher.py` |
| AD-02 | ✅ | claude | Al alcanzar umbral: avisar por COMMS (Telegram) + notificación PC + badge en web | `app/comms/*`, `apps/web/*`, `main.py` |
| AD-03 | ✅ | claude | No spamear: avisar una vez por modelo hasta que se entrene o se descarte | `app/training/threshold_watcher.py` |
| AD-04 | ⬜ | claude | Umbral auto-sugerido y ajustable por el usuario en el menú | `apps/web/*`, `app/training/thresholds.py` |

### AE · Menú Entrenamiento (Ajustes → Entrenamiento)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| AE-01 | ✅ | claude | Sección "Entrenamiento" en Ajustes (web + PC) | `apps/web/*`, `app/widgets/*` |
| AE-02 | ✅ | claude | Lista de modelos con barra de progreso (ejemplos/umbral) + estado | `apps/web/*` |
| AE-03 | ✅ | claude | Badge "✅ listo para entrenar" cuando supera umbral | `apps/web/*` |
| AE-04 | ✅ | claude | Botón "Entrenar <modelo>" → preflight (VRAM/presencia/seguridad/coste) → confirmar | `apps/web/*`, `app/api/*` |
| AE-05 | ⬜ | claude | Vista de progreso del entrenamiento en vivo (loss, paso, ETA, logs) | `apps/web/*` |
| AE-06 | ⬜ | claude | Historial de versiones por modelo (fecha, ejemplos, métricas, activo) | `apps/web/*` |
| AE-07 | ⬜ | claude | Comparativa A/B y botón "promover" / "rollback" | `apps/web/*` |
| AE-08 | ⬜ | claude | Detalle del dataset (abre el editor AC-03) | `apps/web/*` |
| AE-09 | ⬜ | claude | Ajustes avanzados (hiperparámetros) plegables | `apps/web/*` |
| AE-10 | ⬜ | claude | Solo en instancia PC (por seguridad/VRAM): el menú en móvil muestra estado pero "Entrenar" lo lanza el PC | `apps/web/*`, `app/api/relay_connector.py` |

### AF · Motor de entrenamiento (pipeline real)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| AF-01 | ✅ | claude | Orquestador: preflight → preparar dataset → lanzar train → evaluar → promover/rollback | `app/training/orchestrator.py` |
| AF-02 | ✅ | claude | Preflight: usuario presente + VRAM libre + avisar a seguridad (degradar a nube) + espacio SD | `app/training/preflight.py` |
| AF-03 | ✅ | claude | Runner LOCAL QLoRA (modelos que caben; PEFT/bitsandbytes) | `app/training/runner_local.py` |
| AF-04 | ✅ | claude | Runner RUNPOD QLoRA (subir dataset, lanzar pod A100, recoger adapter) | `app/training/runner_runpod.py` |
| AF-05 | ✅ | claude | Decisor local-vs-runpod por VRAM/tamaño/coste | `app/training/orchestrator.py` |
| AF-06 | ✅ | claude | Stream de progreso (loss/paso) hacia la UI | `app/training/orchestrator.py` |
| AF-07 | ⬜ | claude | Merge del adapter → crear nuevo modelo Ollama (Modelfile) | `app/training/merge.py` |
| AF-08 | ✅ | claude | Cancelar/pausar entrenamiento (y reanudar vigilancia local) | `app/training/orchestrator.py` |
| AF-09 | ⬜ | claude | Pausa automática si arranca un juego o el usuario se va (presencia) | `app/training/scheduler.py` |

### AG · Evaluación + promoción + seguridad del proceso
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| AG-01 | ⬜ | claude | Suite de evaluación por modelo (holdout + tareas canónicas) | `app/training/evaluate.py` |
| AG-02 | ⬜ | claude | A/B nuevo-vs-actual; promover SOLO si mejora (umbral de mejora) | `app/training/evaluate.py` |
| AG-03 | ✅ | claude | Versionado de adapters/modelos + rollback 1-click | `app/training/versioning.py` |
| AG-04 | ⬜ | claude | Backup del modelo anterior antes de promover | `app/storage/backup.py` |
| AG-05 | ✅ | claude | Registro de cada entrenamiento (qué datos, hparams, métricas) para auditoría | `app/training/audit.py` |
| AG-06 | ✅ | claude | Tras promover: marcar los ejemplos como "usados" (no re-entrenar con lo mismo) | `app/training_store.py` |
| AG-07 | ✅ | claude | Notificar resultado por comms (mejoró X%, promovido/descartado) | `app/comms/*` |

### AH · Herramientas/tools por modelo (qué tools refuerza cada uno)
| ID | E | Agente | Tarea | Archivos |
|----|---|--------|-------|----------|
| AH-01 | ✅ | claude | Por cada modelo, registrar QUÉ tools usa más (telemetría de uso de tools) | `app/training/tool_usage.py` |
| AH-02 | ⬜ | claude | Generar ejemplos de tool-use EXITOSO (orquestación correcta) como dato de entrenamiento | `app/training_store.py` |
| AH-03 | ⬜ | claude | Entrenar al 24b en mejor SELECCIÓN de tools (del tool_router + resultados) | `app/training/data_map.py` |
| AH-04 | ⬜ | claude | Entrenar al router de tools con sus aciertos/fallos de categoría | `app/training/data_map.py` |
| AH-05 | ⬜ | claude | Métricas: tasa de tool correcta antes/después de entrenar (medir mejora real) | `app/training/evaluate.py` |

---

## 🐈 RECONOCIMIENTO DE GATOS + APRENDIZAJE DE PATRONES (visión de Steve)
> 3 capas: DETECCIÓN (hay gato y dónde) → RE-ID (cuál gato, por embedding+pelaje)
> → TRACKING (trayectoria). Patrones = auto-supervisado: el modelo predice el
> movimiento, comprueba si se cumple (feedback +/-), aprende por repetición.
> Genérico por especie + refinamiento por individuo. OpenCV en Python (cv2).
> Solo añadir tareas (compañeros activos).

### AI · Detección de animales (capa 1)
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AI-01 | ✅ 100% claude | Detector de objetos animal/gato (YOLO o VLM ligero) → bounding box + score | `app/security/detect.py` |
| AI-02 | ✅ 100% claude | Filtro especie (gato vs persona vs otro) y multi-instancia (varios gatos a la vez) | `app/security/detect.py` |
| AI-03 | ✅ 100% claude | Detección eficiente: corre tras el motion CPU (solo frames con movimiento) | `app/security/vision_pipeline.py` |
| AI-04 | ✅ 100% claude | Recorte del animal (crop) normalizado para re-ID | `app/security/detect.py` |

### AJ · Re-identificación (capa 2: cuál gato)
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AJ-01 | ✅ 100% claude | Alta de mascota: subir fotos por gato (varias poses) en la UI | `apps/web/*`, `app/security/pets.py` |
| AJ-02 | ✅ 100% claude | Extraer EMBEDDING del recorte (encoder visual) y guardar referencias por gato | `app/security/reid.py` |
| AJ-03 | ✅ 100% claude | Features extra del pelaje: histograma de color + patrón (manchas/rayas) | `app/security/reid.py` |
| AJ-04 | ✅ 100% claude | Proporciones corporales (relación cabeza/cuerpo, tamaño relativo) | `app/security/reid.py` |
| AJ-05 | ✅ 100% claude | Matcher: similitud coseno embedding + pelaje + proporciones → cuál gato (con umbral de confianza) | `app/security/reid.py` |
| AJ-06 | ✅ 100% claude | "Desconocido" si ninguna referencia supera el umbral (gato nuevo / intruso animal) | `app/security/reid.py` |
| AJ-07 | ✅ 100% claude | Aprendizaje continuo: confirmaciones del usuario añaden referencias (mejora re-ID) | `app/security/reid.py`, `training_store` |
| AJ-08 | ⬜ | UI: confirmar/corregir "¿es Michi?" → feedback que refina el matcher | `apps/web/*` |

### AK · Tracking + comprensión espacial (capa 3)
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AK-01 | ✅ 100% claude | Tracker multi-objeto (ByteTrack/SORT): enlaza detecciones en tracks por frame | `app/security/tracker.py` |
| AK-02 | ✅ 100% claude | Trayectoria por gato (secuencia de posiciones + tiempo) | `app/security/tracker.py` |
| AK-03 | ✅ 100% claude | Mapa espacial de la habitación (homografía/zonas) → coordenadas normalizadas | `app/security/space_map.py` |
| AK-04 | ✅ 100% claude | Occupancy grid / heatmap de dónde va cada gato | `app/security/space_map.py` |
| AK-05 | ✅ 100% claude | Detección de lugares de descanso ("lugares seguros") por permanencia | `app/security/patterns.py` |
| AK-06 | ✅ 100% claude | Asociar trayectorias con zonas dibujadas (peligrosas/seguras) | `app/security/zones.py` |

### AL · Aprendizaje de patrones (auto-supervisado)
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AL-01 | ✅ 100% claude | Predictor de movimiento: dado posición+hora+zona → siguiente posición/zona | `app/security/predictor.py` |
| AL-02 | ✅ 100% claude | Bucle auto-feedback: predice → espera → compara con real → ejemplo +/- al training_store | `app/security/predictor.py`, `training_store` |
| AL-03 | ✅ 100% claude | Contador de aciertos/fallos del predictor por gato (señal de aprendizaje) | `app/training/registry.py` (stats en predictor.py) |
| AL-04 | ✅ 100% claude | Patrones por FRECUENCIA: zonas/horas habituales, rutas comunes | `app/security/patterns.py` |
| AL-05 | ✅ 100% claude | Priors por ESPECIE (gato: altura, sol, comida, sigilo) como base | `app/security/species_priors.py` |
| AL-06 | ✅ 100% claude | Refinamiento por INDIVIDUO sobre los priors (cada gato su modelo) | `app/security/patterns.py` |
| AL-07 | ✅ 100% claude | Detección de ANOMALÍA: comportamiento fuera del patrón aprendido → posible problema | `app/security/anomaly.py` |
| AL-08 | ⬜ | Dataset del predictor visual → entra en el subsistema de entrenamiento (umbral propio) | `app/training/data_map.py` |
| AL-09 | ⬜ | Visualización de patrones en el dashboard (heatmap, rutas, horarios por gato) | `apps/web/*` |

### AM · Seguridad de los gatos (acción sobre patrones)
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AM-01 | ✅ 100% claude | Alerta si un gato entra en zona peligrosa (cocina/enchufes/TV) | `app/security/anomaly.py`, `app/comms/*` |
| AM-02 | ✅ 100% claude | Predicción preventiva: si el patrón sugiere que VA hacia zona peligrosa, avisar/disuadir antes | `app/security/predictor.py` |
| AM-03 | ⬜ | Disuasión interior por escenario (altavoz: sonidos para separar gatos / alejarlos de peligro) | `app/security/deterrence_tools.py` |
| AM-04 | ⬜ | Modo noche: usar dispositivos de disuasión interior (próximamente) según patrón nocturno | `app/security/deterrence_tools.py` |
| AM-05 | ⬜ | Detección de problemas: rotura, desorden, anomalía en la escena (no solo el gato) | `app/security/analysis_interior.py` |
| AM-06 | ⬜ | Informe diario de los gatos (dónde estuvieron, incidencias, salud aparente) por comms | `app/comms/*`, `app/security/report.py` |

---

## 📨 NOTIFICACIONES / COMUNICACIONES TELEGRAM PROFESIONAL (visión de Steve)
> Lo profesional: UN supergrupo FORO (Topics) con 1 bot → hilos separados por
> importancia (Urgente/Seguridad/Notif/Gatos/Periódico/Sistema). Niveles de
> importancia con sonido/silencio. Panel de comandos por mensaje (inline
> keyboards) "en respuesta a". Aprovechar TODO Telegram. Fallback si no hay
> Topics: prefijo de severidad + panel inline. Solo añadir tareas.

### AN · Transporte Telegram avanzado (Topics + envío)
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AN-01 | ✅ 100% claude | Detectar/crear supergrupo FORO con Topics; guardar chat_id + thread_ids por categoría | `app/comms/telegram_topics.py` |
| AN-02 | ✅ 100% claude | Enviar a un TEMA concreto (message_thread_id) según categoría/importancia | `app/comms/telegram_topics.py` |
| AN-03 | ✅ 100% claude | Fallback sin Topics: prefijo de severidad (🔴🛡️🔔📊) + mismo bot, un chat | `app/comms/telegram_topics.py` |
| AN-04 | ✅ 100% claude | Soporte multi-canal futuro (2º bot / canales aparte) sin reescribir el router | `app/comms/router.py` (arquitectura lista) |
| AN-05 | ✅ 100% claude | Crear los temas por defecto: Urgente, Seguridad, Notificaciones, Gatos, Periódico, Sistema | `app/comms/setup.py` |

### AO · Niveles de importancia + entrega
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AO-01 | ⬜ | Enum de severidad: CRÍTICA, ALTA, MEDIA, BAJA, PERIÓDICA | `app/comms/levels.py` |
| AO-02 | ⬜ | Mapear severidad→tema + sonido (disable_notification) + pin | `app/comms/router.py` |
| AO-03 | ⬜ | CRÍTICA: sonido + pin + (opcional) repetir hasta ACK | `app/comms/router.py` |
| AO-04 | ⬜ | BAJA/PERIÓDICA: silenciosa + va a DIGEST (no mensaje suelto) | `app/comms/digest.py` |
| AO-05 | ⬜ | Editar-en-sitio: una alerta evoluciona (analizando→resuelto) sin spamear | `app/comms/telegram.py` |
| AO-06 | ⬜ | Reglas por FUENTE (agente/error/seguridad/gatos) → severidad por defecto editable | `app/comms/rules.py` |

### AP · Panel de comandos por mensaje (inline keyboards "en respuesta a")
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AP-01 | ⬜ | Inline keyboard genérico por tipo de alerta (botones de acción) | `app/comms/keyboards.py` |
| AP-02 | ⬜ | Acciones seguridad: Confirmar · Ignorar · Ver cámara · Silenciar 1h · Escalar · Disuadir | `app/comms/keyboards.py` |
| AP-03 | ⬜ | Acciones agente: Aprobar · Rechazar · Ver detalle · Reintentar | `app/comms/keyboards.py` |
| AP-04 | ⬜ | Handler de callback_query: ejecuta la acción y edita el mensaje con el resultado | `app/comms/callbacks.py` |
| AP-05 | ⬜ | Las acciones peligrosas pasan por aprobación (DANGEROUS) y/o 2FA | `app/comms/callbacks.py` |
| AP-06 | ⬜ | Confirmaciones de seguridad alimentan training_store (feedback) | `app/comms/callbacks.py`, `training_store` |

### AQ · Digest / agrupación / anti-flood
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AQ-01 | ⬜ | Buffer de notificaciones BAJA/PERIÓDICA → resumen cada N min/horas | `app/comms/digest.py` |
| AQ-02 | ⬜ | Agrupar repetidas (mismo evento N veces) en una sola con contador | `app/comms/dedup.py` |
| AQ-03 | ⬜ | Rate-limit (respetar límites de Telegram) + cola con reintento | `app/comms/telegram.py` |
| AQ-04 | ⬜ | Resumen diario programado (estado casa, gatos, sistema) | `app/comms/digest.py` |
| AQ-05 | ⬜ | Horario "no molestar" (solo CRÍTICA suena de noche) | `app/comms/rules.py` |

### AR · Comandos del bot (menú + control)
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AR-01 | ⬜ | Menú de comandos (BotCommands): /estado /resumen /silenciar /modo /camara /ayuda | `app/comms/commands.py` |
| AR-02 | ⬜ | /silenciar <cat> <tiempo> → muta una categoría temporalmente | `app/comms/commands.py` |
| AR-03 | ⬜ | /modo <manual|operativa|alto-impacto> → autonomía de seguridad en caliente | `app/comms/commands.py` |
| AR-04 | ⬜ | /camara <nombre> → snapshot/stream + panel de acciones | `app/comms/commands.py` |
| AR-05 | ⬜ | /resumen → digest bajo demanda; /estado → salud del sistema | `app/comms/commands.py` |
| AR-06 | ⬜ | Chat libre con el AGENTE desde Telegram (texto → brain_bridge → respuesta) | `app/comms/chat.py` |
| AR-07 | ⬜ | Reacciones (👍/👎) como feedback rápido → training_store | `app/comms/reactions.py` |

### AS · Config + permisos + UI del módulo comms
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AS-01 | ⬜ | Config de comms en Ajustes (web/PC): temas, severidades por fuente, no-molestar, digest | `apps/web/*`, `app/widgets/*` |
| AS-02 | ⬜ | Auth: solo admin ejecuta acciones; viewers solo ven (reutiliza 2FA/vault) | `app/comms/auth.py` |
| AS-03 | ⬜ | Registro/auditoría de notificaciones enviadas y acciones ejecutadas | `app/comms/audit.py` |
| AS-04 | ⬜ | Plantillas de mensaje por tipo (formato/emoji/campos) editables | `app/comms/templates.py` |
| AS-05 | ⬜ | Test de notificación (enviar de prueba a cada tema) desde la UI | `apps/web/*` |

---

## 🔊 DISUASIÓN EXTERIOR — actuadores abstractos + audio (visión de Steve)
> Realidad: 1 cámara Tapo (ampliable), HA limitado, altavoz de cámara NO sirve.
> Palanca: altavoz POTENTE de casa por BT (o altavoces del sistema). Enfoque:
> abstraer disuasión del HW → la IA razona "intención/nivel", la capa de
> ACTUADORES la traduce a lo disponible (degradación elegante BT→sistema→nada).
> Escala a N cámaras con actuadores asignados. Solo añadir tareas.

### AT · Capa de actuadores (abstracción de hardware)
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AT-01 | ⬜ | Interfaz `DeterrenceActuator` (capabilities, is_available, fire(intent)) | `app/security/actuators/base.py` |
| AT-02 | ⬜ | Registro de actuadores disponibles + asignación POR CÁMARA | `app/security/actuators/registry.py` |
| AT-03 | ⬜ | Degradación elegante: elegir el mejor actuador disponible para una intención | `app/security/actuators/registry.py` |
| AT-04 | ⬜ | Estado/salud de cada actuador (BT conectado? altavoz vivo? HA online?) | `app/security/actuators/registry.py` |
| AT-05 | ⬜ | UI: asignar actuadores a una cámara + test de disparo | `apps/web/*` |

### AU · Audio (camino principal HOY)
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AU-01 | ⬜ | Reproductor de audio del PC con selección de dispositivo de salida (Windows) | `app/security/audio/player.py` |
| AU-02 | ⬜ | Actuador AltavozBluetooth (pair/route + reproducir) | `app/security/actuators/bt_speaker.py` |
| AU-03 | ⬜ | Actuador AltavozSistema (fallback) | `app/security/actuators/system_speaker.py` |
| AU-04 | ⬜ | Biblioteca de sonidos por ESCENARIO (sirena, ladrido, alarma, aviso) + gestor | `app/security/audio/library.py` |
| AU-05 | ⬜ | TTS local (edge-tts/pyttsx3) → voz por el altavoz elegido | `app/security/audio/tts.py` |
| AU-06 | ⬜ | TTS EN VIVO: la IA narra lo que ve (descripción del intruso) en tiempo real | `app/security/audio/live_narrate.py` |
| AU-07 | ⬜ | Multi-idioma + voces configurables | `app/security/audio/tts.py` |
| AU-08 | ⬜ | Reconexión BT automática (si se cae, reintenta o cae a sistema) | `app/security/actuators/bt_speaker.py` |

### AV · Actuadores HA + futuros
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AV-01 | ⬜ | Actuador LuzHA (encender luces como presencia/aviso) | `app/security/actuators/ha_light.py` |
| AV-02 | ⬜ | Actuador SirenaHA (si algún modelo lo soporta; detectar capacidad) | `app/security/actuators/ha_siren.py` |
| AV-03 | ⬜ | Mapear funciones REALES y aprovechables de la Tapo vía HA (auditar qué llega) | `docs/TAPO_HA.md` |
| AV-04 | ⬜ | Actuador genérico "enchufe inteligente" (foco potente/estrobo futuro) | `app/security/actuators/smart_plug.py` |
| AV-05 | ⬜ | Actuador Láser/LuzBT (futuro, interfaz lista) | `app/security/actuators/light_bt.py` |
| AV-06 | ⬜ | Plantilla para añadir un actuador nuevo (doc + clase base) | `docs/ADD_ACTUATOR.md` |

### AW · Lógica de disuasión (la IA decide)
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AW-01 | ⬜ | Niveles de disuasión: 1 presencia → 2 audio → 3 narración → 4 luz → 5 escalar | `app/security/deterrence.py` |
| AW-02 | ⬜ | La IA elige el nivel según amenaza/zona/hora/contexto de la cámara | `app/security/deterrence.py` |
| AW-03 | ⬜ | Escalado automático si la amenaza persiste (sube de nivel) | `app/security/deterrence.py` |
| AW-04 | ⬜ | De-escalado/cancelar si la amenaza desaparece o el usuario lo para | `app/security/deterrence.py` |
| AW-05 | ⬜ | Tools de disuasión para el agente (deter_warn, deter_sound, deter_narrate, deter_light) | `app/security/deterrence_tools.py`, `app/tools.py` |
| AW-06 | ⬜ | Contexto editable por cámara (qué hay, qué se permite disuadir, límites) | `apps/web/*`, `cameras_db` |
| AW-07 | ⬜ | Modo "solo avisar al usuario" (sin disuasión activa) configurable | `app/security/deterrence.py` |
| AW-08 | ⬜ | Registro de cada disuasión (qué nivel, qué actuador, resultado) → training_store | `app/security/deterrence.py`, `training_store` |

### AX · Seguridad/legalidad de la disuasión
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AX-01 | ⬜ | Límites configurables (no disuadir en zonas públicas, horarios, intensidad) | `app/security/deterrence_limits.py` |
| AX-02 | ⬜ | Confirmación humana para niveles altos (láser/sirena) salvo modo autónomo | `app/security/deterrence.py` |
| AX-03 | ⬜ | Aviso legal: la narración informa de grabación (cumplimiento) | `app/security/audio/library.py` |
| AX-04 | ⬜ | Cooldown anti-abuso (no disparar en bucle) | `app/security/deterrence.py` |

---

## 🎛️ MENÚ DISUASIÓN + ACTUADORES POR CÁMARA (visión de Steve)
> En la vista de cada cámara: menú con los actuadores que TENEMOS (si hay más, más;
> si no, lo que haya). Por cada actuador se DESCRIBE el comportamiento esperado →
> el agente designado lo CABLEA y TESTEA → cuando está en VERDE es que funciona y
> se puede emitir PRUEBA real. Incluye añadir dispositivos inteligentes (casquillos/
> enchufes) a HA desde el propio menú. Solo añadir tareas.

### AY · Menú de disuasión en la vista de cámara
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AY-01 | ⬜ | Panel "Disuasión" en la vista de cámara: lista de actuadores asignados + estado (rojo/ámbar/verde) | `apps/web/*` |
| AY-02 | ⬜ | Añadir actuador a la cámara (elegir de los disponibles del sistema) | `apps/web/*`, `actuators/registry` |
| AY-03 | ⬜ | Por actuador: campo "comportamiento esperado" (texto) que el agente usa para cablear/testear | `apps/web/*`, `cameras_db` |
| AY-04 | ⬜ | Botón "Cablear/Configurar" → el agente designado conecta el actuador real | `app/security/actuators/wire.py` |
| AY-05 | ⬜ | Botón "Probar" (emite prueba real: sonido/narración/luz) — habilitado solo si VERDE | `apps/web/*`, `actuators/registry` |
| AY-06 | ⬜ | Semáforo de estado: ROJO (sin cablear) · ÁMBAR (cableado, sin verificar) · VERDE (test OK) | `app/security/actuators/registry.py` |
| AY-07 | ⬜ | Editor de niveles: qué actuadores dispara cada nivel de disuasión (1..5) por cámara | `apps/web/*` |
| AY-08 | ⬜ | Presets rápidos: "narración + ladridos + luces" (lo que Steve quiere de salida) | `apps/web/*`, `deterrence` |

### AZ · Auto-cableado + test por el agente (verde = funciona)
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| AZ-01 | ⬜ | El agente lee "comportamiento esperado" → genera la integración del actuador | `app/security/actuators/wire.py` |
| AZ-02 | ⬜ | Auto-test del actuador (dispara y verifica respuesta) → marca VERDE/rojo con evidencia | `app/security/actuators/selftest.py` |
| AZ-03 | ⬜ | Reporte del test (qué hizo, qué se esperaba, resultado) visible en el menú | `apps/web/*` |
| AZ-04 | ⬜ | Re-test bajo demanda + auto-test periódico de salud del actuador | `app/security/actuators/selftest.py` |
| AZ-05 | ⬜ | Si un actuador pasa a ROJO (se desconectó), avisar por comms y degradar | `app/comms/*`, `actuators/registry` |

### BA · Añadir dispositivos inteligentes a HA desde el menú
| ID | E | Tarea | Archivos |
|----|---|-------|----------|
| BA-01 | ⬜ | Descubrir entidades HA disponibles (luces, enchufes, switches) y listarlas | `app/security/ha_discovery.py` |
| BA-02 | ⬜ | "Añadir dispositivo": vincular una entidad HA (casquillo/enchufe inteligente) como actuador | `apps/web/*`, `actuators/ha_light`, `actuators/smart_plug` |
| BA-03 | ⬜ | Asistente para emparejar un dispositivo NUEVO en HA (guía/llamada a HA) | `app/security/ha_pairing.py` |
| BA-04 | ⬜ | Probar el dispositivo recién añadido (on/off/parpadeo) desde el menú | `apps/web/*` |
| BA-05 | ⬜ | Catálogo de tipos soportados (luz, enchufe, sirena, switch) extensible | `app/security/actuators/catalog.py` |
| BA-06 | ⬜ | Guardar dispositivos añadidos en el vault/config (credenciales HA reutilizadas) | `app/secrets_vault.py`, `cameras_db` |
