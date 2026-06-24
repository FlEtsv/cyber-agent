# TASKBOARD listener

`scripts/taskboard_listener.py` vigila `TASKBOARD.md` y emite eventos JSONL cuando Steve cambia objetivos, aprueba tareas o un agente mueve trabajo entre estados.

Es read-only: no edita el board, no ejecuta tareas y no toca prompts ni comportamiento del modelo.

## Uso rapido

Desde `C:\Users\steve\cyber-llm\agent-native`:

```powershell
.venv\Scripts\python.exe scripts\taskboard_listener.py --agent codex
```

Para Claude:

```powershell
.venv\Scripts\python.exe scripts\taskboard_listener.py --agent claude
```

Para ver todo:

```powershell
.venv\Scripts\python.exe scripts\taskboard_listener.py --agent all
```

## Lectura puntual

```powershell
.venv\Scripts\python.exe scripts\taskboard_listener.py --agent codex --once
```

## Salidas

El listener imprime una linea JSON por evento y tambien escribe en:

```text
logs/taskboard_listener.log
```

El estado local para comparar cambios queda en:

```text
data/taskboard_listener_state.json
```

Ambos son artefactos locales. No deben subirse al repo.

## Eventos principales

- `baseline`: estado inicial al arrancar.
- `objective_changed`: cambio en `OBJETIVOS`.
- `task_approved`: Steve marco una tarea con `✅`.
- `task_unapproved`: una tarea dejo de estar aprobada.
- `task_changed`: cambio una fila de tarea.
- `in_progress_changed`: cambio `EN PROGRESO`.
- `completed_changed`: cambio `COMPLETADO`.
- `blocked_changed`: cambio `BLOQUEADO`.

## Flujo recomendado

1. Steve edita `TASKBOARD.md`.
2. El listener muestra el evento.
3. El agente lee `TASKBOARD.md`, `AGENTS.md` y `git log --oneline -5`.
4. El agente reclama la tarea en `EN PROGRESO`.
5. Trabaja, verifica, mueve a `COMPLETADO` y commitea.
