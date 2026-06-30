# SECURITY_MODULE.md — Arquitectura del Módulo de Seguridad (M-03)

## Visión general

El módulo de seguridad de CyberAgent (`app/security/`) es el cerebro de la vigilancia
del hogar. Integra cámaras, IA de visión, notificaciones Telegram y disuasión activa,
todo gateado por la variable `SECURITY_ENABLED=1`.

---

## Capas del sistema

```
Cámaras (RTSP/HA)
      │
      ▼
  motion_cpu.py  ← Detección de movimiento en CPU (OpenCV, 0 VRAM)
      │ movimiento detectado
      ▼
  vision_pipeline.py  ← Cola backpressure; samplea frames
      │
      ├──► [GPU libre]  vision_local.py  (VLM local, ~2.5GB VRAM)
      └──► [GPU ocupada] brain_bridge.py → Mistral nube (Pixtral)
                │
                ▼
          decision.py  ← Parser acción/confianza/motivo
                │
          events.py ring-buffer  ← Histórico + SSE
                │
      ┌─────────┴─────────┐
      ▼                   ▼
  deterrence.py    comms/router.py
  (disuasión)       (Telegram + web)
      │
  actuators/
  registry.py  ← Degradación elegante (BT→sistema→HA→nada)
```

---

## Módulos principales

| Módulo | Descripción |
|--------|-------------|
| `camera.py` | Snapshot/RTSP/clip vía HA o ffmpeg |
| `motion_cpu.py` | Detección de movimiento en CPU (OpenCV diff frames) |
| `vision_pipeline.py` | Cola de frames + coordinación GPU/nube |
| `vision_local.py` | VLM local (Moondream2/Qwen2.5-VL) para triage |
| `vision_router.py` | Router GPU-libre→local, GPU-ocupada→nube |
| `brain_bridge.py` | Puente al agente local y a Mistral Pixtral (nube) |
| `events.py` | Ring-buffer D-01/D-02; emit/subscribe/recent |
| `deterrence.py` | Lógica de disuasión AW-01..08 (5 niveles) |
| `actuators/` | Capa de actuadores HW (BT, HA, sistema) |
| `analysis_exterior.py` | Análisis de personas (descripción policial) |
| `analysis_interior.py` | Detección de gatos, anomalías, peligros |
| `detect.py` | YOLO/VLM: bounding boxes de animales/personas |
| `reid.py` | Re-identificación de gatos por embedding+pelaje |
| `tracker.py` | ByteTrack: trayectorias multi-objeto |
| `space_map.py` | Heatmap de ocupación + rutas |
| `patterns.py` | Aprendizaje de patrones por gato |
| `anomaly.py` | Detección de comportamiento anómalo |
| `zones.py` | Zonas dibujables (WARNING/SEGURA) + punto-en-polígono |
| `recorder.py` | Grabación H.265 + retención legal 15 días |
| `report.py` | Informe diario de gatos por comms |
| `legal_limits.py` | Límites de disuasión (horario, intensidad, aviso legal) |
| `gpu_broker.py` | Árbitro de VRAM usuario↔seguridad |

---

## Flujo de alertas

1. **Motion detectado** → motion_cpu.py dispara
2. **Triage visual** → VLM local (presencia/movimiento/tipo)
3. **Si persona** → brain_bridge → Pixtral nube → descripción policial
4. **Parser** → decision.py extrae threat_score, action, description
5. **Disuasión** → deterrence.trigger(cam_id, threat_score)
6. **Notificación** → comms/router.py → Telegram (tema Seguridad)
7. **Registro** → events.emit + training_store.record_decision

---

## Gating de seguridad

Todo el módulo requiere `SECURITY_ENABLED=1` en el entorno.
Por defecto está `0` — el módulo arranca pero no procesa nada.

Los secretos se acceden siempre vía `app.secrets_vault.get_secret(key)`.
Nunca directamente con `os.environ`.

---

## Variables de entorno relevantes

| Variable | Default | Descripción |
|----------|---------|-------------|
| `SECURITY_ENABLED` | `0` | Activa/desactiva el módulo |
| `LIVE_BRAIN_INTERVAL` | `5` | Segundos entre análisis IA en vivo |
| `MAX_LIVE_SESSIONS` | `4` | Sesiones SSE simultáneas de cámara |
| `GO2RTC_HOST` | `localhost` | Host del proxy go2rtc |
| `GO2RTC_PORT` | `1984` | Puerto de go2rtc |

Los secretos (`SEC_TELEGRAM_TOKEN`, `SEC_HA_TOKEN`, etc.) se almacenan
en el vault cifrado y se recuperan con `get_secret("SEC_*")`.

---

## Añadir un actuador nuevo

Ver `docs/ADD_ACTUATOR.md` para la guía paso a paso.

---

## Retención legal de vídeo

Por ley española, el vídeo de vigilancia debe conservarse máximo 30 días
(resolución AEPD). CyberAgent aplica una política por defecto de **15 días**
configurable en `app/storage/retention.py`.

---

*Documento generado automáticamente — M-03*
