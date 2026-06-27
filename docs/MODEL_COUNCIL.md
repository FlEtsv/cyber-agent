# Model Council

CyberAgent now supports a local-first model council:

- `richardyoung/qwen3-14b-abliterated:Q5_K_M`: fast local/private worker for most tool use, code edits, quick audits, and iterative tasks.
- `cyberagent-original`: local/private power model for long context and heavier analysis already present in this system.
- Mistral Studio via `mistral_consult`: external reviewer for second opinions, threat modeling, architecture, debugging, and audit blind spots.

## Privacy Rules

- Local models stay first for files, secrets, credentials, internal code, and active tooling.
- Mistral is exposed as a high-risk `ask` tool because it sends data to an external API.
- `mistral_consult` redacts likely secrets by default.
- Use `allow_sensitive=true` only after explicit user approval for the exact context being sent.
- API keys are read only from environment variables and must never be committed.

## Setup

Install the fast Qwen worker:

```powershell
.\scripts\setup_model_council.ps1 -Pull
```

Use it in the current shell:

```powershell
$env:CYBERAGENT_FAST_MODEL='richardyoung/qwen3-14b-abliterated:Q5_K_M'
$env:CYBERAGENT_POWER_MODEL='cyberagent-original'
$env:CYBERAGENT_MISTRAL_MODEL='mistral-large-latest'
$env:MISTRAL_API_KEY='<set locally>'
```

Persist non-secret model defaults:

```powershell
.\scripts\setup_model_council.ps1 -PersistEnv
```

The script intentionally does not persist `MISTRAL_API_KEY`.

## Routing

The tool router exposes `mistral_consult` for:

- Explicit Mistral/council/second-opinion requests.
- Security audit and pentest workflows where an external reviewer can identify blind spots.

The local agent still decides whether to request it, and the normal permission gate requires approval before the cloud call runs.
