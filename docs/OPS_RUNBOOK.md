# Windows/Web Operations Runbook

This runbook is for daily logistics on the Windows CyberAgent node. It excludes `ios/`.

## Health Check

```powershell
cd C:\Users\steve\cyber-llm\agent-native
.\scripts\ops_health.ps1 -Detailed
```

Checks:

- Python processes that belong to this project.
- Duplicate logical `main.py`, API, and `taskboard_listener.py` instances. Raw counts can be `2` when the venv launcher has a child process; logical counts are the operational signal.
- Local API readiness at `http://127.0.0.1:8765/api/status`, with `localhost` fallback.
- Ollama readiness at `http://127.0.0.1:11434/api/tags`, with `localhost` fallback.
- Active model environment defaults.
- TCP listener on port `8765`.

Machine-readable output:

```powershell
.\scripts\ops_health.ps1 -Json
```

## Controlled Restart

Restart the full Windows desktop agent:

```powershell
.\scripts\restart_windows_instance.ps1 -KeepTaskboardListener
```

Restart only the local API helper:

```powershell
.\scripts\restart_windows_instance.ps1 -ApiOnly -KeepTaskboardListener
```

Preview what would be stopped without changing anything:

```powershell
.\scripts\restart_windows_instance.ps1 -DryRun
```

The restart script only targets Python processes whose command line contains this project path and one of:

- `main.py`
- `uvicorn app.api.server`
- `scripts/start_local_api.py`
- `scripts/taskboard_listener.py` unless `-KeepTaskboardListener` is passed

## Expected Model Setup

```powershell
$env:CYBERAGENT_FAST_MODEL='richardyoung/qwen3-14b-abliterated:Q5_K_M'
$env:CYBERAGENT_POWER_MODEL='cyberagent-original'
$env:CYBERAGENT_MISTRAL_MODEL='mistral-large-latest'
```

`MISTRAL_API_KEY` must stay local and must not be committed.

## Quick Recovery

1. Run `.\scripts\ops_health.ps1 -Detailed`.
2. If duplicates or stale listeners appear, run:

```powershell
.\scripts\restart_windows_instance.ps1 -KeepTaskboardListener
```

3. Verify:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/status
ollama list
```
