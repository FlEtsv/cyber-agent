# 👁️ Modelo de visión local — evaluación y estrategia (T-01, V-05)

> Triage de vigilancia continuo y barato en local + análisis profundo en nube.
> GPU RTX 5080 16 GB compartida con el cerebro (cyberagent-24b). Objetivo: vigilar
> sin robar VRAM ni latencia al usuario.

## 1. Esquema por niveles (recordatorio de arquitectura)

| Nivel | Modelo | Dónde | Cuándo | Coste |
|-------|--------|-------|--------|-------|
| 0 · Movimiento | OpenCV (frame diff) | **CPU** | continuo | $0, 0 VRAM |
| 1 · Triage | VLM local ligero | **GPU si libre** | solo con movimiento | $0 |
| 1' · Triage (GPU ocupada) | Pixtral | **NUBE** | movimiento + usuario infiriendo | bajo |
| 2 · Análisis profundo | Pixtral | **NUBE** | solo si triage marca amenaza | bajo (raro) |

## 2. Candidatos a VLM local de triage

| Modelo | Params | VRAM aprox | Velocidad | Notas |
|--------|--------|-----------|-----------|-------|
| **Moondream2** | ~1.8B | ~2.5 GB (Q) | muy rápida | Pensado para describir/“¿qué hay?”; ideal triage |
| **Qwen2.5-VL 3B** | ~3B | ~4 GB (Q) | rápida | Mejor razonamiento visual; algo más pesado |
| LLaVA-Phi / similar | ~3B | ~4 GB | media | Alternativa |

**Recomendación:** **Moondream2** para el triage continuo (presencia / ¿persona o
gato? / ¿movimiento relevante?). Si se necesita más detalle local sin ir a nube,
**Qwen2.5-VL 3B** como segundo escalón. El análisis serio (descripción policial,
amenaza, decisión de disuasión) SIEMPRE va a **Pixtral nube**.

## 3. Co-residencia en 16 GB (V-05)

| Combinación | VRAM estimada | ¿Cabe en 16 GB? |
|-------------|---------------|-----------------|
| cyberagent-24b Q3_K_M | ~11 GB | sí (margen ~5 GB) |
| + Moondream2 Q | +~2.5 GB | **sí** (~13.5 GB, margen ~2.5 GB) |
| + Qwen2.5-VL 3B Q | +~4 GB | justo (~15 GB) — preferir solo con GPU poco usada |
| cyberagent-24b Q4_K_M (~14 GB) + VLM | >16 GB | **no** → por eso el cerebro va en Q3 |

**Conclusión:** el cerebro en **Q3 deja sitio al ojo local** (Moondream2) → pueden
convivir y vigilar mientras el usuario usa el agente. Es una razón extra del Q3.
Validar VRAM real con `nvidia-smi` tras cargar ambos (tarea de verificación).

## 4. Prioridad de GPU (resumen del broker — V-02/V-04)

1. El **usuario tiene prioridad**. Si infiere, el triage de seguridad va a **nube**.
2. Si la GPU está libre, el triage usa el VLM local (gratis).
3. **Modo juego**: se libera el 24B; la seguridad va 100% a nube/CPU.
4. Nunca se bloquea la inferencia del usuario por la vigilancia.

## 5. Integración (T-02/T-03/T-04)

- `app/security/vision_local.py` → carga/consulta el VLM local de triage (Ollama).
- `app/security/vision_router.py` → decide local vs nube según `gpu_broker`.
- `app/security/brain_bridge.py` → análisis profundo a Pixtral nube (`SEC_MISTRAL_VISUAL_MODEL`).
- `app/security/vision_pipeline.py` → frame sampling (no cada frame), cola, backpressure.

## 6. Pasos de instalación (cuando se active la visión local)

```
ollama pull moondream        # ~1.7 GB
# (opcional) ollama pull qwen2.5vl:3b
```
Configurar `CYBERAGENT_VISION_LOCAL_MODEL=moondream` y activar
`CYBERAGENT_SECURITY_ENABLED=1`. El router elegirá local/nube automáticamente.
