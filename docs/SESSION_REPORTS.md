# Session reports

CyberAgent can generate lightweight session reports from the browser UI and from the local agent log.

## Web and mobile UI

The chat header includes a `Reporte` button. It downloads a JSON report with:

- session start/end timestamps
- device and browser context
- user and assistant messages from the current browser session
- tool calls, status, completion/cancel state, and short result previews
- connection and error events

The report is generated locally in the browser. It does not require a Cloud Run round trip.

## Local diagnostic log

`app.agent_log.build_report()` returns a redacted JSON-compatible report from `agent.log`.
Sensitive fields such as passwords, tokens, cookies, API keys, TOTP secrets and JWTs are redacted before export.

Example:

```python
from app.agent_log import write_report

write_report("reports/agent-log-report.json", max_lines=500)
```

## Scope

This report is for debugging and traceability. It is not a full audit archive and should not be treated as a secure evidence store.
