# TAPO_HA.md — Integración Tapo con Home Assistant (AV-03)

## Cámara Tapo C200/C310 — Capacidades reales vía HA

### ¿Qué hace la Tapo en HA?

| Función | Estado | Notas |
|---------|--------|-------|
| Snapshot | ✅ Funciona | `camera.snapshot` → imagen JPEG |
| Stream RTSP | ✅ Funciona | `rtsp://user:pass@ip:554/stream1` |
| Detección de movimiento (webhook) | ✅ Funciona | `binary_sensor.tapo_motion` en HA |
| Zoom digital | ⚠️ Parcial | Sólo C310 con PTZ |
| PTZ (pan/tilt) | ✅ C310 | `camera.turn_on` no aplica; usar servicio PTZ |
| Grabación en SD | ✅ Local | No accesible vía HA |
| TTS por el altavoz de la cámara | ❌ No | El altavoz Tapo no es accionable vía HA |
| Luz IR (infrarrojo) | ⚠️ Limitado | `switch.tapo_night_mode` en algunos modelos |
| Sonido de sirena integrada | ❌ No | Tapo no expone sirena vía HA |

### Integración recomendada

```yaml
# configuration.yaml (Home Assistant)
camera:
  - platform: ffmpeg
    name: Cam Entrada
    input: rtsp://admin:TU_PASS@192.168.1.100:554/stream1
```

Para la detección de movimiento, el integration Tapo (HACS o nativo)
expone `binary_sensor.tapo_cam_entrada_motion`.

### Limitaciones de la Tapo para disuasión

La cámara Tapo **no tiene altavoz accionable** desde HA.
Para disuasión por audio, usa:
1. Altavoz Bluetooth del sistema (bt_speaker.py)
2. Altavoz del PC (system_speaker.py)
3. Media player de HA (si está disponible en otra entidad)

### Snapshot vía CyberAgent

```python
from app.security.camera import snapshot_by_name
image_b64 = snapshot_by_name("cam_entrada")
```

### Stream en tiempo real

CyberAgent usa **go2rtc** como proxy RTSP→WebRTC/HLS.
Configurar en `integrations/security/go2rtc.yaml`:

```yaml
streams:
  cam_entrada:
    - rtsp://admin:PASS@192.168.1.100:554/stream1
```

Acceder desde el dashboard: `http://localhost:1984/api/stream.m3u8?src=cam_entrada`

---

*AV-03 — Auditoría Tapo HA — CyberAgent Security Module*
