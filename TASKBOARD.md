# TASKBOARD — CyberAgent Multi-Agent Board

> Documento de coordinación en tiempo real entre Claude Code, Codex y el Director (Steve).
> Ambos agentes leen este archivo completo al inicio de cada turno antes de hacer cualquier cosa.

---

## 📜 REGLAS — Vigentes desde aprobación del Director

> Estas reglas están activas. Steve las aprueba asignando tareas en el BACKLOG con `✅`.
> Los agentes las siguen sin necesidad de confirmación adicional.

**R1 — Declara antes de actuar.**
Antes de tocar cualquier archivo, escribe en `EN PROGRESO` qué vas a hacer, en qué archivos y por qué. Sin esa entrada no se empieza nada.

**R2 — Declara si tocas zona ajena.**
Si necesitas modificar un archivo que pertenece al otro agente (ver `AGENTS.md`), hazlo — pero escríbelo explícitamente en tu entrada de `EN PROGRESO` y en el mensaje del commit. No pides permiso, lo declaras.

**R3 — No dejes tareas a medias.**
Si empiezas, terminas: código completo, sintaxis verificada, commit hecho, tarea movida a `COMPLETADO`. Si surge un bloqueante real, muévela a `BLOQUEADO` con explicación clara.

**R4 — No alteres filtros de comportamiento ni ética de modelos.**
Ningún agente modifica system prompts de comportamiento interno, filtros de seguridad del LLM ni parámetros que cambien cómo razona el modelo. Sin excepciones.

**R5 — Lee el board primero, siempre.**
Al iniciar sesión: leer `TASKBOARD.md` → leer `AGENTS.md` → `git log --oneline -5`. Solo después actuar.

**R6 — El director manda.**
Las directivas de Steve en `OBJETIVOS` tienen prioridad absoluta. Si no hay objetivo activo, tomar la tarea de mayor prioridad `✅` del BACKLOG que corresponda a tu zona.

**R7 — Formato de commit obligatorio.**
`[claude] tipo: descripción` o `[codex] tipo: descripción`. Tipos: `feat`, `fix`, `security`, `docs`, `refactor`.

**R8 — SESION TERMINADA.**
Si Steve escribe esas palabras en `OBJETIVOS`, ambos agentes paran, commitean el estado actual (marcando lo incompleto), y no inician tareas nuevas.

---

## 🎯 OBJETIVOS

> **Steve escribe aquí.** Los agentes leen esto primero en cada sesión.
> Si hay texto aquí, tiene prioridad sobre todo el BACKLOG.

    Actualizar el Gui de todo la app, darle una estetica sofisticada y elegante.
    Diseñar seguridad de fugas de datos. 
    Proteccion contra errores de corrupcion de datos.
    Implementar sistema de reportes. 
    Integrar las herramientas de Hacking. 
    Realizar pruebas automatizadas.
    




## 🔄 EN PROGRESO

> Escribe aquí ANTES de tocar cualquier archivo.
> Formato: `[AGENTE] ID — Qué voy a hacer — Archivos: x, y — Fecha: YYYY-MM-DD HH:MM`
> Si tocas zona ajena: añadir `⚠️ zona ajena: motivo`

[claude] B003 — SYSTEM_PROMPT con fecha fija al arranque — no se actualiza en sesiones largas — Archivos: `app/ollama_client.py`, `app/api/agent_runner.py` — Fecha: 2026-06-24 22:09

---

## ✅ COMPLETADO

> Mover aquí desde EN PROGRESO al terminar.
> Formato: `[AGENTE] ID — Descripción — Commit: abc1234 — Fecha: YYYY-MM-DD HH:MM`

*(vacío)*

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
8. Mover a COMPLETADO + commit del TASKBOARD
```
