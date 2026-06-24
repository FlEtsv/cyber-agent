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

    Actualizar el Gui de todo la app, darle una estetica sofisticada y elegante.✅
    Diseñar seguridad de fugas de datos. ✅
    Proteccion contra errores de corrupcion de datos.✅
    Realizar pruebas automatizadas.✅
    dejar interfaces listas para conectar con el PC en local o PC en la nube, con la guia de uso correcta y clara.✅
    dejar claro el modo de uso para el usuario final.✅
    Asegurar que cada agente sepa actuar en su campo.✅
    conseguir que cada agente tenga su manual de instrucciones claro.✅
    Asegurar que cada agente tenga su espacio de archivos limpio y ordenado.✅
    lolos agentes son los modelos de IA con los que se conecta el usuario final, no solo los que componen el sistema.✅
    

    


## ✅ OBJETIVOS IMPLEMENTADOS

> Los agentes mueven aquí objetivos globales cuando el desglose asociado está completado y verificado.

Implementar sistema de reportes. Cerrado por `REP-001` con export JSON/HTML desde web/local/relay, reporte local desde `agent.log`, redacción de secretos y documentación en `docs/SESSION_REPORTS.md`.
Integrar las herramientas de Hacking. Cerrado por `TOOL-001` con catálogo de herramientas, permisos por riesgo, grupo router `hacking`, metadatos en UI/logs y `docs/TOOLS.md`.
Conseguir suit de herramientas global de precision. Cerrado por `TOOL-001` con catálogo estructurado de 75 herramientas y routing explícito por categorías.
Actualizar como funciona cada herramienta y hacer un manual de uso. Cerrado por `TOOL-001` con `docs/TOOLS.md` y guías por categoría.
Improved del LLM de decisión de herramientas. Cerrado por `TOOL-001` con keywords de hacking/pentest/recon y selección combinada web+network+forensics.




## 🔑 PERMISOS SOLICITADOS

> **Steve:** pon `✅` para autorizar el commit, o ignora si estás en dev — el agente pasa a la siguiente tarea y hace commit acumulado cuando llegue el tick.
> Formato: `[AGENTE] ID — "descripción exacta del commit" — Fecha HH:MM`
> Regla obligatoria: los agentes no piden estos permisos por chat. Solo añaden/modifican filas aquí y actúan cuando ven `✅`.

[claude] TEST-001+DATA-001+SEC-001 — "push git origin master (commit 9c92360)" — Fecha: 2026-06-24 22:58

---

## 🔄 EN PROGRESO

> Escribe aquí ANTES de tocar cualquier archivo.
> Formato: `[AGENTE] ID — Qué voy a hacer — Archivos: x, y — Fecha: YYYY-MM-DD HH:MM`
> Si tocas zona ajena: añadir `⚠️ zona ajena: motivo`

*(vacío)*

---

## ✅ COMPLETADO

> Mover aquí desde EN PROGRESO al terminar.
> Formato: `[AGENTE] ID — Descripción — Commit: abc1234 — Fecha: YYYY-MM-DD HH:MM`

`[CODEX] INFRA-001 — Listener read-only de TASKBOARD.md — Commit: 831bae3 — Fecha: 2026-06-24 22:14`
[claude] B001+B007 — Backoff exponencial (5→10→20→40→60s) + cleanup runners al desconectar — Commit: c842ed7 — Fecha: 2026-06-24 22:20
[claude] B002 — CORS dinámico _DynamicCORS lee env por req (no import-time) — Commit: c842ed7 — Fecha: 2026-06-24 22:20
[claude] B003+F002 — AgentWorker llama _build_base_prompt() por turno (fecha actual en cada mensaje) — Commit: c842ed7 — Fecha: 2026-06-24 22:20
[claude] F003 — FAST_MODEL/POWER_MODEL configurables via CYBERAGENT_*_MODEL env — Commit: c842ed7 — Fecha: 2026-06-24 22:20
[codex] B004+B005+B006+UI-001 — Reconexión frontend, banners PC/reconectando y pulido visual web/relay — Commit: 3cc9d5b — Fecha: 2026-06-24 22:35
[codex] UI-002 — Rediseño GUI desktop PySide: cabecera workspace, navegación, estados y tema visual — Commit: 0d54b7c — Fecha: 2026-06-24 22:50
[codex] UI-003 — Rediseño login/PWA móvil local y relay con estado Cloud Run/PC/iPhone — Commit: 230564a — Fecha: 2026-06-24 22:58
[claude] TEST-001+DATA-001+SEC-001 — tests auth 12/12 + integrity_check/backup_db + redacción tokens en logs — Commit: 9c92360 — Fecha: 2026-06-24 22:58
[claude] SEC-003+SEC-004 — Sanitizar errores HTTP + rate limiting relay — Commit: bbaff5b — Fecha: 2026-06-24 23:10
[codex] REP-001 — Sistema de reportes de sesión con export JSON/HTML, redacción y documentación — Commit: 777592d — Fecha: 2026-06-24 23:20
`[codex] TOOL-001 — Catálogo hacking/tools con permisos por riesgo, routing, UI y manual — Commit: 777592d — Fecha: 2026-06-24 22:52 — ⚠️ zona ajena: app/ollama_client.py y app/api/agent_runner.py para propagar metadatos de eventos`

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
```


## 📌 PERMISOS Y PETICIONES

Se dejan las acciones que se necesita que el usuario apruebe como peticiones en el área de permisos y peticiones abajo, tomad los objetivos genericos como que teneis que desglosarlo como tareas de implementacion, haceis desgloses añadís en tareas de backlog y yo las apruebo asi todo el rato.

**Prohibido pedir estos permisos por chat.** El chat no es un canal de aprobación. Si falta un `✅`, el agente registra la petición aquí y continúa con otra tarea aprobada. Si el `✅` ya está puesto, ejecuta directamente y actualiza el estado.

| ID | ✅ | Agente | Acción solicitada | Estado |
|----|----|--------|-------------------|--------|
| P-CODEX-001 | ✅ | codex | Ejecutar `node --check app/web/static/app.js` y `node --check relay/web/app.js`; si pasan, hacer commit acumulado `[codex] feat: improve web reconnect and visual states` con B004+B005+B006+UI-001 y actualización del TASKBOARD. | completado: 3cc9d5b |
| P-CODEX-002 | ✅ | codex | Ejecutar validación de sintaxis Python para `app/widgets/main_window.py` y `app/styles.py`; si pasa, commit `[codex] feat: refine desktop gui shell` con UI-002 y actualización del TASKBOARD. | completado: 0d54b7c |
| P-CODEX-003 | ✅ | codex | Ejecutar validación HTML/CSS básica de login local/relay; si pasa, commit `[codex] feat: redesign mobile login surfaces` con UI-003 y actualización del TASKBOARD. | completado: 230564a |
