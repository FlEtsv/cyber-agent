# 📨 Plan de presentación de mensajes — Comunicaciones (U-06)

> Cómo se ve y se entrega cada mensaje según su FUENTE e IMPORTANCIA. Base del
> módulo `app/comms/`. Un supergrupo foro (Topics) + 1 bot; severidad controla
> sonido/pin/digest; cada alerta lleva su panel de acciones inline.

## 1. Severidades (`app/comms/levels.py`)

| Severidad | Valor | Entrega | Sonido | Pin | Tema destino |
|-----------|-------|---------|--------|-----|--------------|
| CRÍTICA | 5 | inmediata | sí | sí (hasta ACK) | 🔴 Urgente |
| ALTA | 4 | inmediata | sí | no | 🛡️ Seguridad / 🔔 Notif |
| MEDIA | 3 | inmediata | normal | no | 🔔 Notificaciones |
| BAJA | 2 | **digest** | silenciosa | no | 📊 Periódico |
| PERIÓDICA | 1 | **digest** | silenciosa | no | 📊 Periódico |

## 2. Severidad por defecto según FUENTE (editable, `app/comms/rules.py`)

| Fuente | Severidad por defecto | Tema |
|--------|----------------------|------|
| Amenaza exterior confirmada | CRÍTICA | 🔴 Urgente |
| Gato en zona peligrosa | ALTA | 🐈 Gatos / 🛡️ Seguridad |
| Warning de cámara (movimiento) | MEDIA | 🛡️ Seguridad |
| Error del sistema crítico | CRÍTICA | 🔴 Urgente |
| Error no crítico | BAJA | ⚙️ Sistema |
| Respuesta de agente (tarea hecha) | MEDIA | 🔔 Notificaciones |
| Aprobación pendiente del agente | ALTA | 🔔 Notificaciones |
| Resumen diario / estado | PERIÓDICA | 📊 Periódico |
| Modelo listo para entrenar | MEDIA | 🔔 Notificaciones |

## 3. Formato de mensaje (plantilla por tipo — AS-04)

**Estructura común:**
```
{emoji} <b>{TÍTULO}</b>
{cuerpo}
{línea de contexto: cámara / hora / fuente}
[ panel de botones inline según tipo ]
```

**Ejemplos:**

- **Amenaza exterior (CRÍTICA):**
  ```
  🔴 <b>PERSONA DETECTADA — entrada</b>
  Hombre, chaqueta roja, merodeando junto a la puerta.
  📷 Cámara Exterior · 02:14 · zona WARNING
  [ Ver cámara ] [ Disuadir ] [ Ignorar ] [ Emergencia ]
  ```
- **Gato en peligro (ALTA):**
  ```
  🐈 <b>Michi cerca de la cocina</b>
  Trayectoria hacia zona peligrosa (fogones).
  📷 Cámara Cocina · 19:40
  [ Ver ] [ Disuadir (sonido) ] [ Ignorar ]
  ```
- **Tarea de agente (MEDIA):**
  ```
  🔔 <b>Tarea completada</b>
  Deploy de la web finalizado. 131 tests verdes.
  [ Ver detalle ] [ 👍 ] [ 👎 ]
  ```
- **Digest (PERIÓDICA):**
  ```
  📊 <b>Resumen — últimas 6 h</b>
  • 3 movimientos (todos descartados)
  • Gatos: actividad normal
  • Sistema: OK
  ```

## 4. Reglas de entrega

- **CRÍTICA**: suena siempre (incluso en "no molestar"); se fija (pin) y puede
  repetirse hasta que el usuario pulse un botón (ACK).
- **BAJA/PERIÓDICA**: nunca mensaje suelto → se acumulan en **digest** (cada N min
  o resumen diario).
- **Repetidas**: el mismo evento N veces se agrupa en una con contador (dedup).
- **No molestar** (horario nocturno): solo CRÍTICA suena; el resto, silencioso.
- **Rate-limit**: respeta los límites de Telegram; cola con reintento.

## 5. Edición en sitio

Una alerta evoluciona editando el mismo mensaje (no spamea):
`⏳ Analizando…` → `🔍 Persona detectada` → `✅ Disuasión aplicada / resuelto`.

## 6. Acciones inline por tipo (`app/comms/keyboards.py`)

| Tipo | Botones |
|------|---------|
| Amenaza exterior | Ver cámara · Disuadir · Ignorar · Escalar · Emergencia |
| Peligro gato | Ver · Disuadir (sonido) · Ignorar |
| Aprobación agente | Aprobar · Rechazar · Ver detalle |
| Notif agente | Ver detalle · 👍 · 👎 (feedback → training_store) |
| Sistema/error | Ver logs · Silenciar 1h |

> Las acciones peligrosas pasan por aprobación/2FA. Las reacciones 👍/👎 alimentan
> el entrenamiento (W).
