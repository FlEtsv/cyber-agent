# ADD_ACTUATOR.md — Cómo añadir un actuador nuevo (AV-06)

## Estructura de un actuador

Todos los actuadores heredan de `DeterrenceActuator` (`app/security/actuators/base.py`).

```python
from app.security.actuators.base import DeterrenceActuator, ActuatorCapabilities, Intent

class MiActuador(DeterrenceActuator):
    name = "mi_actuador"
    capabilities = ActuatorCapabilities(
        intents=[Intent.PRESENCE, Intent.AUDIO_WARN],
        supports_tts=False,
        latency_ms=200,
    )

    def is_available(self) -> bool:
        # Retornar True si el actuador está listo
        return True

    def fire(self, intent: Intent, payload: dict | None = None) -> bool:
        # Ejecutar la intención
        if intent == Intent.PRESENCE:
            # encender luz suave...
            return True
        return False
```

## Niveles de disuasión e intents

| Nivel | Intent | Descripción |
|-------|--------|-------------|
| 1 | PRESENCE | Luz suave — marcar presencia |
| 2 | AUDIO_WARN | Sonido de aviso (ladrido, alarma) |
| 3 | NARRATE | TTS narrando lo que ve la IA |
| 4 | LIGHT | Luz potente / estroboscópica |
| 5 | SIREN | Sirena de alta intensidad |

## Registrar el actuador

```python
from app.security.actuators.registry import register
from app.security.actuators.mi_actuador import MiActuador

register(MiActuador())
```

Registra en el arranque del supervisor (añadir a `app/supervisor.py` bajo el bloque de actuadores).

## Asignar a una cámara

```python
from app.security.actuators.registry import assign_to_camera
assign_to_camera("cam_entrada", ["mi_actuador", "system_speaker"])
```

O desde la UI web: Vista Cámara → sección Disuasión → Añadir actuador.

## Test del actuador

Usar el selftest automatizado:

```python
from app.security.actuators.selftest import run_selftest
result = run_selftest("mi_actuador", cam_id="cam_entrada")
# {"ok": True, "status": "green", ...}
```

O desde la UI web: botón "Probar" en el panel de disuasión (visible solo si status=green).

## Degradación elegante

Si el actuador principal no está disponible (`is_available() → False`),
`registry.best_for(cam_id, intent)` pasa automáticamente al siguiente
en la lista de asignados. Si ninguno está disponible, retorna `None`
y el nivel de disuasión no se ejecuta (silencio seguro).

---

*AV-06 — Plantilla actuadores — CyberAgent Security Module*
