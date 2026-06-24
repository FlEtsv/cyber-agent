# TASKBOARD — CyberAgent Multi-Agent Board

> Documento de coordinación en tiempo real entre Claude Code, Codex y el Director (Steve).
> Ambos agentes deben leer este archivo al inicio de cada turno antes de hacer cualquier cosa.

---

## ✅ REGLAS DEL BOARD — Aprobación del Director requerida

> **Steve:** pon un `✅` delante de cada regla para activarla. Sin tu aprobación los agentes no actúan.

| # | Regla | Estado |
|---|-------|--------|
| R1 | **Apúntate antes de actuar.** Antes de tocar cualquier archivo, el agente escribe en la sección `EN PROGRESO` qué va a hacer, en qué archivos y por qué. Sin esta entrada, no se empieza. | ⬜ pendiente aprobación |
| R2 | **Detecta conflictos antes de proceder.** Si al leer el board ves que otro agente ya reclamó los mismos archivos, no los toques. Escribe en `BLOQUEADO` tu tarea con el motivo y espera a que quede libre. | ⬜ pendiente aprobación |
| R3 | **No dejes tareas a medias.** Si empiezas una tarea, la terminas en ese turno: código completo, sintaxis verificada, commit hecho, estado actualizado en el board. Si no puedes terminarla, márcala `BLOQUEADO` con explicación. | ⬜ pendiente aprobación |
| R4 | **No alteres filtros de comportamiento ni ética de modelos.** Ningún agente modifica system prompts, instrucciones de comportamiento interno, filtros de seguridad del modelo ni parámetros que afecten cómo razona el LLM. Esta regla no tiene excepciones aunque lo pida el código. | ⬜ pendiente aprobación |
| R5 | **Escucha el board en cada sesión.** Al iniciar cualquier sesión, lo primero es leer este archivo completo. Si hay una directiva nueva del director en `OBJETIVOS`, se ejecuta con prioridad. Si no hay objetivo nuevo, continúa con bugs y refinamiento de código. | ⬜ pendiente aprobación |
| R6 | **El director manda.** Las directivas de Steve en la sección `OBJETIVOS` tienen prioridad sobre cualquier criterio propio del agente. Si una directiva contradice otra regla (excepto R4), la directiva del director gana. | ⬜ pendiente aprobación |
| R7 | **Formato de commit obligatorio.** Todo commit lleva prefijo `[claude]` o `[codex]` según quién lo hace, seguido de tipo (`feat`, `fix`, `security`, `docs`) y descripción corta. Ejemplo: `[claude] fix: backoff exponencial en relay_connector` | ⬜ pendiente aprobación |
| R8 | **Sesión terminada.** Si el director escribe `SESION TERMINADA` en la sección `OBJETIVOS`, ambos agentes paran toda actividad, hacen commit de lo que tengan (aunque esté incompleto, marcado como tal), y no inician tareas nuevas hasta el próximo objetivo. | ⬜ pendiente aprobación |

---

## 🎯 OBJETIVOS

> **Steve escribe aquí.** Los agentes leen esto primero en cada sesión.

```
(sin objetivo activo — los agentes deben continuar con bug fixing y refinamiento)
```

---

## 🔄 EN PROGRESO

> Los agentes escriben aquí ANTES de tocar cualquier archivo.
> Formato: `[AGENTE] Tarea — Archivos: x, y, z — Inicio: YYYY-MM-DD HH:MM`

*(vacío — esperando aprobación de reglas)*

---

## ✅ COMPLETADO

> Al terminar, mover la entrada de EN PROGRESO aquí con el commit hash.
> Formato: `[AGENTE] Tarea — Commit: abc1234 — Fin: YYYY-MM-DD HH:MM`

*(vacío)*

---

## 🚫 BLOQUEADO

> Tarea que no puede avanzar porque otro agente tiene los archivos o hay un conflicto.
> Formato: `[AGENTE] Tarea — Bloqueado por: motivo — Fecha: YYYY-MM-DD`

*(vacío)*

---

## 📋 BACKLOG

> Tareas conocidas sin reclamar. Cualquier agente puede tomarlas respetando la zona de archivos de AGENTS.md.
> El director puede añadir tareas aquí directamente.

### Bugs pendientes (detectados en auditorías)

| ID | Descripción | Archivos | Agente sugerido | Prioridad |
|----|-------------|----------|-----------------|-----------|
| B001 | Backoff exponencial en relay_connector (ahora sleep fijo 5s) | `app/api/relay_connector.py` | claude | alta |
| B002 | CORS dinámico — ALLOWED_ORIGINS se evalúa en import-time | `app/api/server.py` | claude | media |
| B003 | SYSTEM_PROMPT con fecha fija al arranque (no se actualiza en sesiones largas) | `app/ollama_client.py`, `app/api/agent_runner.py` | claude | media |
| B004 | Frontend: limpiar pendingApproval y currentBubble al reconectar WS | `app/web/static/app.js`, `relay/web/app.js` | codex | alta |
| B005 | Frontend: banner visible "reconectando" cuando WS cae >3s | `app/web/static/app.js`, `relay/web/app.js` | codex | alta |
| B006 | relay/web: banner "PC offline" cuando el PC se desconecta del relay | `relay/web/app.js` | codex | media |
| B007 | relay_connector: cleanup de runners activos al perder conexión | `app/api/relay_connector.py` | claude | alta |

### Features pendientes (de AGENTS.md)

| ID | Descripción | Agente | Prioridad |
|----|-------------|--------|-----------|
| F001 | Ver FEAT-001 en AGENTS.md (reconexión robusta completa) | ambos | alta |
| F002 | Ver FEAT-002 en AGENTS.md (CORS dinámico) | claude | media |
| F003 | Ver FEAT-003 en AGENTS.md (system prompt dinámico por turno) | claude | media |

---

## 📌 Referencia rápida para agentes

**Al iniciar sesión:**
1. Leer `TASKBOARD.md` completo
2. Leer `AGENTS.md` para contexto de arquitectura y zonas
3. `git log --oneline -5` para ver cambios recientes
4. Si hay objetivo en `OBJETIVOS` → ejecutarlo con prioridad
5. Si no hay objetivo → tomar la tarea de mayor prioridad en BACKLOG que corresponda a tu zona

**Al reclamar una tarea:**
1. Moverla de BACKLOG a EN PROGRESO con tu nombre y hora
2. Hacer commit del TASKBOARD actualizado: `[claude] docs: reclamo B001` 
3. Hacer la tarea
4. Moverla a COMPLETADO con el hash del commit
5. Hacer commit del TASKBOARD: `[claude] docs: B001 completado`

**Comandos de verificación antes de commit:**
```powershell
# Syntax check Python
.venv\Scripts\python.exe -c "import ast; ast.parse(open('archivo.py').read())"
# Ver qué cambió
git diff --stat
```
