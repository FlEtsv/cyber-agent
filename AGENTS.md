# AGENTS.md — CyberAgent Collaboration Protocol

> **Este archivo es la fuente de verdad para la colaboración entre agentes y el director del proyecto.**
> El director (Steve) añade features y prioridades en la sección ROADMAP.
> Claude Code y Codex leen este archivo al inicio de cada sesión y actualizan su sección de estado.

---

## 👤 Director del Proyecto

**Steve** — añade features, cambia prioridades, aprueba merges, resuelve conflictos entre agentes.

**Cómo contribuir como director:**
- Añade features en la sección `## ROADMAP` con el formato definido
- Cambia el estado de una feature de `[ ]` a `[x]` cuando esté hecha
- Añade notas o restricciones en la feature usando el campo `notes`
- Commitea el cambio o edita directamente en GitHub

---

## 🤖 Agentes

### Claude Code
- **Especialidad:** Seguridad, arquitectura backend, refactoring complejo, auditorías, contexto amplio del codebase
- **Zona principal:** Motor del agente, API server, Auth, Consciousness, relay backend
- **Cómo actuar:** Lee este archivo, mira el estado del repo (`git log --oneline -10`), toma las tareas marcadas `claude` sin preguntar
- **Actualiza:** La sección `### Estado Claude` al terminar cada tarea

### Codex
- **Especialidad:** Implementación de features discretas, frontend JS/HTML/CSS, tools individuales, tests
- **Zona principal:** Tools layer, RAG, Fine-tuning, PWA frontend, utilidades del sistema
- **Cómo actuar:** Lee este archivo, toma las tareas marcadas `codex` sin preguntar, abre PR al terminar
- **Actualiza:** La sección `### Estado Codex` al terminar cada tarea

---

## 📁 Mapa de Propiedad de Archivos

> Si un agente toca un archivo fuera de su zona, lo indica en su sección de estado.
> Los archivos sin asignar (`-`) puede tocarlos cualquiera — avisar en el commit message.

| Área | Archivos | Agente |
|------|----------|--------|
| Entrypoint | `main.py` | ambos (coordinado) |
| Motor agente | `app/ollama_client.py`, `app/model_router.py`, `app/react_parser.py` | claude |
| API server | `app/api/server.py`, `app/api/agent_runner.py`, `app/api/relay_connector.py` | claude |
| API utils | `app/api/alert_sender.py`, `app/api/approval_poller.py`, `app/api/tunnel.py` | claude |
| Auth | `app/auth.py` | claude |
| Consciousness | `app/consciousness/*.py` | claude |
| Relay cloud | `relay/main.py`, `relay/generate_secrets.py` | claude |
| Relay web | `relay/web/*.js`, `relay/web/*.html`, `relay/web/*.css` | codex |
| Tools | `app/tools.py`, `app/tool_router.py`, `app/mobile_tools.py` | codex |
| RAG | `app/rag/*.py`, `app/autonomous_learner.py` | codex |
| Fine-tuning | `app/finetune/*.py` | codex |
| GUI widgets | `app/widgets/*.py` | codex |
| PWA frontend | `app/web/*.html`, `app/web/static/*.js`, `app/web/static/*.css`, `app/web/sw.js` | codex |
| Database | `app/database.py`, `app/memory.py`, `app/agent_log.py` | ambos |
| Utilidades | `app/autostart.py`, `app/updater.py`, `app/ollama_keepalive.py` | codex |
| Estilos | `app/styles.py` | codex |
| Instalador | `installer/installer_gui.py` | codex |

---

## 🔄 Protocolo de Comunicación

### Cómo coordinar sin bloquearse

1. **Antes de tocar un archivo ajeno** — abrir un Issue en GitHub mencionando el archivo y por qué
2. **Al terminar una tarea** — commit con prefijo `[claude]` o `[codex]` + actualizar sección de estado aquí
3. **Si hay conflicto de merge** — el director decide, no los agentes
4. **Para preguntar al otro agente** — crear un Issue con label `question` mencionando al agente en el título
5. **Para proponer una arquitectura** — crear Issue con label `design` antes de implementar

### Formato de commit

```
[claude] fix: descripcion corta
[codex] feat: descripcion corta
[claude] security: descripcion
```

### Cuándo abrir PR vs commit directo

- **Commit directo a master:** bugfixes urgentes, cambios en archivos de tu zona
- **PR obligatorio:** cambios que tocan archivos de la zona del otro agente, features nuevas grandes, cambios de arquitectura

---

## 🏗️ Arquitectura del Proyecto

```
CyberAgent v5 — Windows 11 + RTX 5080 16GB
├── main.py                    ← QApplication, tray, mutex instancia única
├── app/
│   ├── ollama_client.py       ← AgentWorker QThread, tool-calling nativo Qwen2.5
│   ├── tools.py               ← 38+ herramientas (shell, file, web, security, RAG...)
│   ├── mobile_tools.py        ← ADB Android + SSH iOS
│   ├── auth.py                ← bcrypt + TOTP 2FA + JWT HS256 72h
│   ├── database.py            ← SQLite WAL, threading.local() connections
│   ├── memory.py              ← build_layered_history(), summarize_messages()
│   ├── autonomous_learner.py  ← DuckDuckGo → ChromaDB, 14 topics, cada 30min
│   ├── api/
│   │   ├── server.py          ← FastAPI :8765, WS chat + terminal, auth
│   │   ├── agent_runner.py    ← AgentRunner sin Qt (para web/relay)
│   │   └── relay_connector.py ← PC → Cloud Run (outbound WS)
│   ├── consciousness/
│   │   ├── self_awareness.py  ← listado/modificación/reinicio propios archivos
│   │   ├── system_context.py  ← system prompt dinámico con fecha/hora/hardware
│   │   ├── threat_detector.py ← detección LLM de actividad sospechosa
│   │   └── decision_log.py    ← log de decisiones del agente en SQLite
│   ├── rag/
│   │   ├── vectorstore.py     ← ChromaDB + DefaultEmbeddingFunction (onnxruntime)
│   │   ├── retriever.py       ← top-3 docs relevantes por consulta
│   │   └── knowledge_base.py  ← seed inicial de documentos
│   ├── web/                   ← PWA servida por FastAPI (app.js, sw.js, login.html)
│   └── widgets/               ← PySide6 GUI (MainWindow, ChatPanel, TerminalPanel...)
└── relay/
    ├── main.py                ← Cloud Run FastAPI relay (JWT, bcrypt, TOTP, WS bridge)
    └── web/                   ← Frontend del relay (app.js, login.html)
```

**Stack:**
- Python 3.14 · PySide6 (Qt6) · FastAPI · uvicorn · httpx · SQLite
- Ollama local: `cyberagent-original` (Qwen2.5-32B abliterated Q3_K_M)
- ChromaDB + onnxruntime (sin scipy — bloqueado por AppControl)
- Google Cloud Run · Cloudflare Tunnel · bcrypt · pyotp · python-jose

**URLs:**
- Relay: `https://cyberagent-relay-819820880956.us-central1.run.app`
- Local API: `http://localhost:8765`
- Ollama: `http://localhost:11434`

---

## 📋 ROADMAP — Features y Tareas

> **Steve:** añade features aquí. Formato obligatorio para que los agentes las entiendan.

### Cómo añadir una feature

```markdown
### FEAT-XXX: Nombre de la feature
- **Prioridad:** alta | media | baja
- **Asignado a:** claude | codex | ambos
- **Estado:** [ ] pendiente | [~] en progreso | [x] done
- **Descripción:** Qué debe hacer exactamente
- **Archivos afectados:** lista de archivos (si lo sabes)
- **Criterio de éxito:** cómo saber que está hecha
- **Notes:** restricciones, ideas, contexto
```

---

### FEAT-001: Reconexión robusta WebSocket
- **Prioridad:** alta
- **Asignado a:** ambos
- **Estado:** [~] en progreso
- **Descripción:**
  - `[claude]` `relay_connector.py`: backoff exponencial (5s→10s→20s→max 60s), cleanup runners al desconectar
  - `[codex]` `app.js` + `relay/web/app.js`: limpiar pendingApproval en onclose, banner "reconectando" visible, limpiar currentBubble/toolRows en onopen, banner "PC offline" en relay
- **Archivos afectados:** `app/api/relay_connector.py`, `app/web/static/app.js`, `relay/web/app.js`
- **Criterio de éxito:** el cliente móvil muestra estado claro cuando cae el WS; el PC reconecta sin duplicar runners
- **Notes:** Ver Issue #1 para contexto detallado

---

### FEAT-002: CORS dinámico en servidor local
- **Prioridad:** media
- **Asignado a:** claude
- **Estado:** [ ] pendiente
- **Descripción:** `app/api/server.py` — ALLOWED_ORIGINS construido en import-time; si CYBERAGENT_CLOUD_URL no está en .env al arrancar, el relay queda bloqueado por CORS. Mover a función que se evalúa en cada request o recargar en caliente desde env.
- **Archivos afectados:** `app/api/server.py`
- **Criterio de éxito:** requests desde el relay funcionan sin necesidad de reiniciar el servidor si se cambia la URL
- **Notes:** —

---

### FEAT-003: System prompt con fecha actualizada por conversación
- **Prioridad:** media
- **Asignado a:** claude
- **Estado:** [ ] pendiente
- **Descripción:** `SYSTEM_PROMPT` se construye en import-time con fecha fija. En sesiones largas la fecha/hora del prompt envejece. Llamar `_build_base_prompt()` al inicio de cada turno del agente en lugar de usar la constante global.
- **Archivos afectados:** `app/ollama_client.py`, `app/api/agent_runner.py`
- **Criterio de éxito:** el system prompt refleja la hora actual en cada mensaje enviado a Ollama
- **Notes:** `system_context.py` ya tiene `_build_system_prompt()` dinámico — ver si se puede reutilizar

---

<!-- AÑADE NUEVAS FEATURES AQUÍ -->

---

## 📊 Estado de los Agentes

### Estado Claude
```
Última actualización: 2026-06-24
Últimas tareas completadas:
  - Auditoría rondas 8-11: 39 bugs corregidos (commits a68ea33..75dcedd)
  - CORS, auth, reconexión backend, RAG locks, DB transactions
Tarea actual: creación de AGENTS.md y sistema de colaboración
Bloqueado por: nada
Próxima tarea: FEAT-001 (relay_connector backoff), FEAT-002 (CORS dinámico)
```

### Estado Codex
```
Última actualización: 2026-06-21 (estimado)
Últimas tareas completadas:
  - OCR/Tesseract support
  - Desktop visual control tools
  - Mobile Ollama assistant history normalization
  - winget fix + PATH refresh
Tarea actual: desconocido
Bloqueado por: desconocido
Próxima tarea: FEAT-001 (frontend reconexión), pendiente de leer este archivo
```

---

## 🚫 Zonas de No-Toque

Estos archivos/datos **nunca** deben estar en commits:

- `.env` — contiene RELAY_HOST_SECRET y otras claves
- `data/jwt_secret.txt` — secreto JWT local
- `data/credentials.json` — hash bcrypt + TOTP secret
- `data/chroma/` — base de datos vectorial local
- `cyberagent.db` — base de datos SQLite con historial

---

## 🔧 Setup para Agentes Nuevos

Si es tu primera sesión en este proyecto:

```powershell
# 1. Verificar entorno
cd C:\Users\steve\cyber-llm\agent-native
.venv\Scripts\python.exe --version  # debe ser 3.14

# 2. Ver estado actual
git log --oneline -10
git status

# 3. Verificar Ollama
curl http://localhost:11434/api/tags

# 4. Leer archivos clave antes de tocar nada
# - main.py (entrypoint)
# - app/ollama_client.py (motor)
# - app/api/server.py (API)
# - relay/main.py (relay cloud)
```

**Variables de entorno necesarias** (en `.env` local, NO en repo):
```
RELAY_URL=wss://cyberagent-relay-819820880956.us-central1.run.app
RELAY_HOST_SECRET=<secret>
```
