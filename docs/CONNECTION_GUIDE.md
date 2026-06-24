# Guía de conexión — CyberAgent

Cómo conectar al agente desde cualquier dispositivo y entorno: PC local, red LAN, iPhone o cualquier lugar del mundo via Cloud Run.

---

## Arquitectura de conexión

```
iPhone / Navegador remoto
        │
        ▼
┌─────────────────────┐
│   Cloud Run Relay   │  ← cyberagent-relay (Google Cloud)
│   (JWT + bcrypt)    │
└─────────────────────┘
        │  WebSocket seguro (wss://)
        ▼
┌─────────────────────┐
│   Windows PC        │  ← CyberAgent principal
│   (Ollama + Tools)  │
└─────────────────────┘
        ▲
        │  HTTP directo (en la misma red)
┌─────────────────────┐
│  Navegador local    │  ← Cualquier dispositivo en LAN
└─────────────────────┘
```

---

## Opción 1 — Conexión local (misma red WiFi/LAN)

**Requisitos:** Estar en la misma red que el PC con CyberAgent activo.

**URL de acceso:**
```
http://192.168.18.240:8765
```

> La IP LAN puede cambiar. Para verificar la IP actual:
> ```powershell
> Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null }
> ```

**Verificar que el agente está activo:**
```powershell
Invoke-RestMethod -Uri http://localhost:8765/api/status
# Resultado esperado: {"status": "ok", "model": "cyberagent-original", ...}
```

**Login local:**
1. Abre `http://[IP_PC]:8765`
2. Introduce usuario y contraseña configurados en `data/credentials.json`
3. Si 2FA está activado, introduce el código TOTP

**Instalar como PWA (Chrome/Edge):**
1. Abre la URL en Chrome
2. Clic en el ícono de instalar (barra de direcciones, a la derecha)
3. O: menú → "Instalar CyberAgent"

---

## Opción 2 — Conexión remota via Cloud Run relay

**Requisitos:** Internet. El PC debe estar encendido y con CyberAgent activo.

**URL del relay:**
```
https://cyberagent-relay-819820880956.us-central1.run.app
```

**Verificar estado del relay y PC:**
```powershell
Invoke-RestMethod -Uri https://cyberagent-relay-819820880956.us-central1.run.app/api/status
# Resultado esperado: {"relay": true, "pc_online": true}
```

Si `pc_online` es `false`, el PC no está conectado al relay (CyberAgent no está corriendo).

**Login relay:**
1. Abre la URL del relay en el navegador
2. Introduce las mismas credenciales del relay (configuradas en Cloud Run como `RELAY_EMAIL` y `RELAY_PW_HASH`)
3. Si 2FA está activado, introduce el código TOTP

**Instalar como PWA en iPhone (Safari):**
1. Abre la URL del relay en Safari
2. Botón compartir (□↑) → "Añadir a la pantalla de inicio"
3. La app aparece en el home screen como cualquier app nativa

---

## Opción 3 — GUI de escritorio (Windows nativo)

**Solo desde el PC directamente.**

**Iniciar manualmente:**
```powershell
cd C:\Users\steve\cyber-llm\agent-native
.venv\Scripts\pythonw.exe main.py
```

**Iniciar en segundo plano (sin ventana de consola):**
```powershell
Start-Process -FilePath "C:\Users\steve\cyber-llm\agent-native\.venv\Scripts\pythonw.exe" `
  -ArgumentList "main.py" `
  -WorkingDirectory "C:\Users\steve\cyber-llm\agent-native" `
  -WindowStyle Hidden
```

**Verificar que está corriendo:**
```powershell
Get-Process -Name python*, pythonw* | Select-Object Id, Name, CPU
```

---

## Configuración de variables de entorno

El PC necesita estos valores en `.env` o `data/.env`:

```env
# URL del relay Cloud Run
RELAY_URL=https://cyberagent-relay-819820880956.us-central1.run.app

# Secreto compartido con el relay (mismo valor que HOST_SECRET en Cloud Run)
RELAY_HOST_SECRET=<valor del secreto>

# Modelos Ollama (opcional — si no se define usa el default)
CYBERAGENT_FAST_MODEL=cyberagent-original
CYBERAGENT_POWER_MODEL=cyberagent-original
```

**El relay Cloud Run necesita estas variables de entorno** (configuradas en GCP Console o `relay/deploy.ps1`):

```env
HOST_SECRET=<mismo valor que RELAY_HOST_SECRET>
RELAY_EMAIL=<email de login>
RELAY_PW_HASH=<hash bcrypt de la contraseña>
JWT_SECRET=<secreto para firmar cookies JWT>
RELAY_TOTP_SECRET=<obligatorio — secreto TOTP base32 del autenticador>

# Desactivar TOTP solo en entornos de desarrollo sin autenticador
# TOTP_OPTIONAL=1
```

> **Seguridad:** A partir de RELAY-SEC-001 el TOTP es **obligatorio por defecto** en el relay.
> Si `RELAY_TOTP_SECRET` no está configurado, todos los logins serán rechazados aunque la
> contraseña sea correcta. Para generar el secreto TOTP:
> ```powershell
> .venv\Scripts\python.exe relay/generate_secrets.py
> ```

---

## Despliegue del relay Cloud Run

Desde el PC Windows:

```powershell
cd C:\Users\steve\cyber-llm\agent-native
.\relay\deploy.ps1 -Project cyberagent-web-2026 -Region us-central1 -ServiceName cyberagent-relay
```

El script construye la imagen Docker, la sube a Artifact Registry y despliega en Cloud Run.

**Requisitos previos:**
- `gcloud` CLI instalado y autenticado: `gcloud auth login`
- Docker Desktop corriendo
- Permisos de despliegue en el proyecto GCP `cyberagent-web-2026`

---

## Conexión desde Mac mini (desarrollo iOS)

El Mac mini conecta al mismo relay Cloud Run. No necesita configuración especial:
1. Abre el navegador y ve a la URL del relay
2. Login con las mismas credenciales
3. El agente del PC procesa las peticiones aunque estés desde el Mac

Para desarrollo iOS nativo con Xcode:
- Consultar `docs/IOS_EXTENSION_PRD.md` para los requisitos de la app nativa
- La app iOS conecta al relay via WebSocket con JWT
- Las operaciones BLE e iOS-específicas requieren la app nativa (la PWA tiene limitaciones en iOS)

---

## Diagnóstico de conexión

### El relay no responde
```powershell
# Verificar servicio Cloud Run
Invoke-RestMethod -Uri https://cyberagent-relay-819820880956.us-central1.run.app/api/status

# Si falla: redesplegar
.\relay\deploy.ps1 -Project cyberagent-web-2026 -Region us-central1 -ServiceName cyberagent-relay
```

### PC no aparece como online en el relay
```powershell
# 1. Verificar que CyberAgent está corriendo
Get-Process -Name python*, pythonw*

# 2. Verificar que Ollama está activo
Invoke-RestMethod -Uri http://localhost:11434/api/tags

# 3. Reiniciar CyberAgent
$pids = (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'main\.py' }).ProcessId
Stop-Process -Id $pids -Force
Start-Process ".venv\Scripts\pythonw.exe" -ArgumentList "main.py" -WorkingDirectory (Get-Location)
```

### Error de autenticación en el relay
- Verifica que `RELAY_HOST_SECRET` en `.env` del PC coincide con `HOST_SECRET` en Cloud Run
- Puedes regenerar el secreto: `.venv\Scripts\python.exe relay\generate_secrets.py`

### Activos estáticos del relay no cargan (CSS/JS 404)
```powershell
# Verificar assets
Invoke-WebRequest -Uri https://cyberagent-relay-819820880956.us-central1.run.app/static/style.css
Invoke-WebRequest -Uri https://cyberagent-relay-819820880956.us-central1.run.app/static/app.js
# Si dan 404: redesplegar el relay
```

### Latencia alta en el chat remoto
El relay de Cloud Run es us-central1 (Iowa). La latencia típica desde España es ~120-150ms.
Para latencia mínima, usa la conexión local (LAN) cuando estés en casa.

---

## Puertos y firewall

| Puerto | Protocolo | Uso | ¿Expuesto? |
|--------|-----------|-----|------------|
| 8765 | TCP (HTTP/WS) | API y chat local | Solo LAN (sin NAT) |
| 11434 | TCP (HTTP) | Ollama API | Solo localhost |
| 443 | TCP (HTTPS) | Cloud Run relay | Internet (HTTPS) |

El PC **no necesita puertos abiertos en el router** gracias a la conexión WebSocket saliente al relay. Solo se necesita acceso al relay desde el PC (salida TCP 443).

---

## Estado de salud del sistema

Verificación completa del sistema:

```powershell
# 1. Relay
Invoke-RestMethod "https://cyberagent-relay-819820880956.us-central1.run.app/api/status"

# 2. Auth del relay
Invoke-RestMethod "https://cyberagent-relay-819820880956.us-central1.run.app/api/auth/status"

# 3. API local
Invoke-RestMethod "http://localhost:8765/api/status"

# 4. Ollama
Invoke-RestMethod "http://localhost:11434/api/tags"
```

**Resultado esperado cuando todo está correcto:**
```json
// /api/status del relay
{"relay": true, "pc_online": true}

// /api/auth/status del relay (TOTP obligatorio por defecto desde RELAY-SEC-001)
{"setup_done": true, "totp_required": true}

// API local
{"status": "ok"}
```
