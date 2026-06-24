# CyberAgent Project Status - 2026-06-24

This document is the handoff snapshot for continuing development from the Mac mini while keeping this Windows PC as the primary always-on CyberAgent node.

## Executive Summary

CyberAgent currently has three active parts:

1. Windows desktop agent in `agent-native`.
2. Cloud Run relay in `agent-native/relay`.
3. Mobile PWA served by the relay and backed by the Windows PC through an outbound WebSocket.

The Windows PC is the main inference and tool-execution node. It should remain the stable machine for Ollama, local files, terminal access, RAG, and desktop UI. The Mac mini should be used for iOS native development only, connecting to the same Cloud Run relay.

Current Cloud Run relay:

- Service: `cyberagent-relay`
- GCP project ID: `cyberagent-web-2026`
- GCP project number: `819820880956`
- Region: `us-central1`
- Stable URL: `https://cyberagent-relay-819820880956.us-central1.run.app`
- Canonical URL observed from deploy: `https://cyberagent-relay-qpjbftmk7a-uc.a.run.app`
- Latest deployed revision during this snapshot: `cyberagent-relay-00004-lwc`

Current Windows node:

- Repo path: `C:\Users\steve\cyber-llm\agent-native`
- Main process: `pythonw.exe main.py`
- Local LAN IP observed on 2026-06-24: `192.168.18.240`
- Primary health check should still be the relay endpoint, not the LAN IP:
  `GET https://cyberagent-relay-819820880956.us-central1.run.app/api/status`

Expected status when healthy:

```json
{"relay": true, "pc_online": true}
```

## Current Verified State

Verified on 2026-06-24 after redeploy and local tool update:

- `/static/style.css` returns HTTP 200.
- `/static/app.js` returns HTTP 200.
- `/static/login.css` returns HTTP 200.
- `/api/auth/status` returns `setup_done: true` and `totp_required: false`.
- `/api/status` returns `relay: true` and `pc_online: true`.
- Python syntax checks pass for:
  - `relay/main.py`
  - `app/api/server.py`
  - `main.py`
- JavaScript syntax checks pass for:
  - `relay/web/app.js`
  - `app/web/static/app.js`
- Desktop-control tools are registered in `TOOLS_SCHEMA` and compile in `app/tools.py`.
- Real local validation detected 2 monitors:
  - `DISPLAY1`: 1080x1920 at `left=1920`, `top=-480`.
  - `DISPLAY2`: 1920x1080 primary at `left=0`, `top=0`.
- `active_window`, `list_windows`, `ui_tree`, and Windows credential metadata lookup have been smoke-tested locally.
- `ocr_screen` captures an image path, but text OCR requires installing Tesseract plus `pytesseract`.

## Secrets And Local Credentials

Secrets are intentionally not documented inline in this file. They are local runtime material.

Known local locations:

- `agent-native\.env`
- `agent-native\data\.env`
- `agent-native\data\relay_secrets.env`
- `agent-native\data\relay_login_credentials.txt`
- `agent-native\data\jwt_secret.txt`

Important environment variables:

```env
RELAY_URL=https://cyberagent-relay-819820880956.us-central1.run.app
RELAY_HOST_SECRET=<same value as Cloud Run HOST_SECRET>
```

Cloud Run runtime variables:

```env
HOST_SECRET=<shared secret for PC host websocket>
RELAY_EMAIL=<login email>
RELAY_PW_HASH=<bcrypt password hash>
JWT_SECRET=<cookie signing secret>
RELAY_TOTP_SECRET=<optional; currently not required in production relay>
```

The relay setup endpoint intentionally returns `Configura credenciales via env vars` because the deployed relay is configured by environment variables instead of first-run web setup.

## Deployment Commands

Deploy relay from the Windows PC:

```powershell
cd C:\Users\steve\cyber-llm\agent-native
.\relay\deploy.ps1 -Project cyberagent-web-2026 -Region us-central1 -ServiceName cyberagent-relay
```

Check relay health:

```powershell
Invoke-RestMethod -Uri https://cyberagent-relay-819820880956.us-central1.run.app/api/status
Invoke-RestMethod -Uri https://cyberagent-relay-819820880956.us-central1.run.app/api/auth/status
```

Check static assets:

```powershell
Invoke-WebRequest -Uri https://cyberagent-relay-819820880956.us-central1.run.app/static/style.css -UseBasicParsing
Invoke-WebRequest -Uri https://cyberagent-relay-819820880956.us-central1.run.app/static/app.js -UseBasicParsing
Invoke-WebRequest -Uri https://cyberagent-relay-819820880956.us-central1.run.app/static/login.css -UseBasicParsing
```

Restart the Windows CyberAgent instance:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'pythonw|python' } | Select-Object ProcessId,Name,ExecutablePath,CommandLine
Stop-Process -Id <cyberagent-pids> -Force
Start-Process -FilePath 'C:\Users\steve\cyber-llm\agent-native\.venv\Scripts\pythonw.exe' -ArgumentList 'main.py' -WorkingDirectory 'C:\Users\steve\cyber-llm\agent-native' -WindowStyle Hidden
```

## Mobile Login

Open from iPhone:

```text
https://cyberagent-relay-819820880956.us-central1.run.app/login
```

The PWA can be added to the iPhone home screen from Safari.

The current web login hides the 2FA field when `/api/auth/status` reports `totp_required: false`. This fixes the previous confusion where the UI asked for a 2FA code that was not configured.

## Recent Fixes Applied

Context and model stability:

- Added layered memory strategy in `app/memory.py`.
- Added conversation memory persistence in `app/database.py`.
- Hardened Ollama chat history normalization in `app/ollama_client.py`.
- Prevented duplicate assistant endings that caused Ollama error:
  `Cannot have 2 or more assistant messages at the end of the list`.
- Reduced context pressure by using short turn windows, accumulated summaries, RAG fragments, and compacted tool results.
- Status events are emitted to UI but not stored as assistant content.

Agent execution:

- Increased long-task iteration/tool limits in the Ollama runner.
- Added status/checkpoint events so the user can see what the agent is doing.
- Tool cards now show action, arguments, and summarized output.
- Web/mobile tool results are visible in the chat action rows.
- Added explicit desktop-control tools for visual operation of the PC:
  - `list_monitors`
  - `active_window`
  - `list_windows`
  - `focus_window`
  - `click_screen`
  - `type_text`
  - `hotkey`
  - `ocr_screen`
  - `ui_tree`
  - `fill_form`
  - `credential_lookup`
- These tools enable workflows such as opening a browser, navigating to a service, filling a login form, searching content, starting playback, entering fullscreen, and validating state with screenshots/UI inspection.
- Screen/keyboard/mouse/credential tools are marked as sensitive in `DANGEROUS_TOOLS`, so the UI can surface approval/visibility for those actions.

Relay and PWA:

- Fixed Cloud Run static asset mount. The relay now serves `/static/*` even though files live directly under `relay/web`.
- Rebuilt and redeployed Cloud Run relay.
- Changed mobile PWA actions to be open by default.
- Added reconnect backoff and outbox behavior to mobile JS.
- Fixed login UX for non-TOTP mode.
- Cleaned corrupted visible text in login page.
- Cleaned visible mojibake/artifacts in mobile PWA chat JS:
  - user avatar now shows `TU`.
  - status says `generando...`.
  - action labels use `accion/acciones`.
  - tool icons use ASCII labels.
  - attachment remove button uses `x`.
- Remaining mojibake in JavaScript comments is non-rendered developer text and does not affect the mobile UI.

Mobile/Ollama stability:

- Fixed the mobile Cloud Run flow error:
  `Cannot have 2 or more assistant messages at the end of the list`.
- Root cause: the mobile `AgentRunner` path could accumulate assistant turns after tool/checkpoint flows.
- Fix: common `normalize_chat_history` now compacts consecutive assistant messages after tool validation before any Ollama request.

Local app bootstrap:

- `.env` and `data\.env` are normalized for `RELAY_URL` and `RELAY_HOST_SECRET`.
- `main.py` strips BOM from environment values.
- The Windows process currently connects outbound to Cloud Run; no inbound port forwarding is required.

## Known Current Limitations

- The PWA cannot provide full native iPhone control. Safari/PWA is useful for chat, camera/file input, mobile UI, and remote control, but it cannot expose all device capabilities.
- The PWA can show screenshots returned by tools, but true realtime video/screen streaming is not implemented yet. The recommended next step is a lightweight "watch mode" that sends screenshots every N seconds and stops on command.
- iOS system-level Bluetooth control is restricted. BLE operations require a native iOS app using CoreBluetooth and user permissions.
- SSH from the iPhone is best implemented in a native companion app or delegated to Shortcuts/installed SSH tooling.
- The relay currently stores only in-memory host/session state. A Cloud Run restart drops active WebSocket sessions, but the PC reconnects automatically.
- The Windows PC is treated as the main inference node. If it is offline, the mobile UI can connect to Cloud Run but cannot run local tools or Ollama.
- `credential_lookup` can list Windows Credential Manager metadata. Browser password reveal is best-effort: modern Chromium passwords may require Local State key/app-bound handling that is not fully implemented yet.
- `ocr_screen` currently requires external OCR dependencies (`tesseract` binary and Python `pytesseract`) to return recognized text.

## Source Of Truth For Liveness

For Mac mini and iPhone development, do not rely primarily on a saved LAN IP. Use the relay:

```http
GET /api/status
```

Response fields:

- `relay`: Cloud Run service is up.
- `pc_online`: Windows host WebSocket is connected.

LAN IP can be useful for local diagnostics when on the same network:

```powershell
Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null }
```

Snapshot value:

```text
Ethernet IPv4: 192.168.18.240
```

## Development Policy For Next Phase

Keep this Windows PC intact as the production-like agent node.

Use the Mac mini for:

- Xcode project creation.
- SwiftUI app development.
- iPhone signing/install through Xcode.
- iOS-specific tool experiments.

The Mac mini should not replace the Windows PC as the main CyberAgent host unless explicitly planned later.
