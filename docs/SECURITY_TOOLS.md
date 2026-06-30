# Security Module — Tool Schemas for the Agent

> L-02: Documentación de herramientas del módulo de seguridad para el modelo.
> El agente puede llamar estas tools cuando `SECURITY_ENABLED=true` (o siempre
> para Telegram, que está activo por defecto).

---

## 🔔 Notificación Telegram

### `security_notify`
Envía una notificación al chat de Telegram configurado.

```json
{
  "name": "security_notify",
  "parameters": {
    "title": {"type": "string", "description": "Título del mensaje"},
    "body":  {"type": "string", "description": "Cuerpo (opcional)"},
    "emoji": {"type": "string", "default": "🔔"}
  }
}
```

---

## 🏠 Home Assistant

### `ha_control`
Controla una entidad de Home Assistant (luces, enchufes, switches…).

```json
{
  "name": "ha_control",
  "parameters": {
    "entity_id": {"type": "string", "description": "p.ej. light.salon"},
    "service":   {"type": "string", "enum": ["turn_on","turn_off","toggle"], "default": "turn_on"},
    "data":      {"type": "object", "description": "Parámetros adicionales del servicio (brightness, color_temp…)"}
  }
}
```

### `ha_speak`
Reproduce un mensaje de texto por voz en un altavoz de Home Assistant.

```json
{
  "name": "ha_speak",
  "parameters": {
    "message":      {"type": "string"},
    "media_player": {"type": "string", "description": "entity_id del media_player; null = primero disponible"},
    "language":     {"type": "string", "default": "es"}
  }
}
```

### `ha_camera`
Obtiene un snapshot o la URL del stream de una cámara de HA.

```json
{
  "name": "ha_camera",
  "parameters": {
    "camera_entity": {"type": "string", "description": "p.ej. camera.exterior"},
    "op":            {"type": "string", "enum": ["snapshot","stream_url"], "default": "snapshot"}
  }
}
```

### `ha_script`
Ejecuta un script de Home Assistant.

```json
{
  "name": "ha_script",
  "parameters": {
    "script_id": {"type": "string", "description": "ID del script sin prefijo 'script.'"},
    "data":      {"type": "object", "description": "Variables para el script (opcional)"}
  }
}
```

---

## 🔊 Disuasión

> **IMPORTANTE**: Las herramientas de disuasión son DANGEROUS. Requieren aprobación
> o modo autónomo activado. Solo se disparan si la cámara tiene actuadores asignados.

### `deter_warn`
Nivel 1: aviso de presencia (sonido suave, luz breve).

```json
{
  "name": "deter_warn",
  "parameters": {
    "cam_id": {"type": "string", "description": "ID de la cámara que detectó la amenaza"}
  }
}
```

### `deter_sound`
Nivel 2: sonido disuasorio por escenario.

```json
{
  "name": "deter_sound",
  "parameters": {
    "cam_id":   {"type": "string"},
    "scenario": {"type": "string", "enum": ["warning","alarm","bark","siren"], "default": "warning"}
  }
}
```

### `deter_narrate`
Nivel 3: narración TTS en vivo describiendo lo que la IA ve.

```json
{
  "name": "deter_narrate",
  "parameters": {
    "cam_id": {"type": "string"},
    "text":   {"type": "string", "description": "Texto a narrar; vacío = IA genera descripción automática"}
  }
}
```

### `deter_light`
Nivel 4: activar luz potente o estrobo asignado a la cámara.

```json
{
  "name": "deter_light",
  "parameters": {
    "cam_id": {"type": "string"}
  }
}
```

---

## 🔧 Actuadores

### `discover_ha_entities`
Lista entidades de Home Assistant disponibles para añadir como actuadores.

```json
{
  "name": "discover_ha_entities",
  "parameters": {
    "domain": {"type": "string", "description": "Filtrar por dominio (light, switch, media_player…); null = todos"}
  }
}
```

### `add_ha_actuator`
Vincula una entidad HA como actuador de disuasión asignable a cámaras.

```json
{
  "name": "add_ha_actuator",
  "parameters": {
    "entity_id": {"type": "string"},
    "label":     {"type": "string", "description": "Nombre descriptivo (p.ej. 'Luz exterior trasera')"}
  }
}
```

### `wire_actuator`
El agente cableа un actuador basándose en el texto de comportamiento esperado.

```json
{
  "name": "wire_actuator",
  "parameters": {
    "cam_id":        {"type": "string"},
    "actuator_name": {"type": "string"},
    "behavior":      {"type": "string", "description": "Texto libre: qué debe hacer este actuador al dispararse"}
  }
}
```

### `selftest_actuator`
Dispara un auto-test del actuador (intención PRESENCE, no destructivo) y devuelve resultado.

```json
{
  "name": "selftest_actuator",
  "parameters": {
    "actuator_name": {"type": "string"},
    "cam_id":        {"type": "string", "description": "Cámara de contexto (opcional)"}
  }
}
```

---

## 📊 Reglas de uso

| Tool | Riesgo | Requires SECURITY_ENABLED | Requires approval |
|------|--------|--------------------------|-------------------|
| `security_notify` | bajo | No (siempre activo) | No |
| `ha_control` | medio | Sí | Sí (DANGEROUS) |
| `ha_speak` | bajo | Sí | No |
| `ha_camera` | bajo | Sí | No |
| `ha_script` | medio | Sí | Sí (DANGEROUS) |
| `deter_warn` | bajo | Sí | No |
| `deter_sound` | medio | Sí | Sí (DANGEROUS) |
| `deter_narrate` | bajo | Sí | No |
| `deter_light` | medio | Sí | Sí (DANGEROUS) |
| `discover_ha_entities` | ninguno | No | No |
| `add_ha_actuator` | bajo | No | No |
| `wire_actuator` | bajo | No | No |
| `selftest_actuator` | bajo | No | No |

---

## 🔑 Variables de entorno requeridas

Todas las claves se leen vía `app.secrets_vault.get_secret()` con prefijo `SEC_`:

| Variable | Uso |
|----------|-----|
| `SEC_TELEGRAM_BOT_TOKEN` | Token del bot de Telegram |
| `SEC_TELEGRAM_CHAT_ID` | Chat ID principal |
| `SEC_HA_URL` | URL base de Home Assistant (p.ej. `http://homeassistant.local:8123`) |
| `SEC_HA_TOKEN` | Long-lived access token de HA |
| `SEC_MISTRAL_API_KEY` | Clave Mistral para análisis de visión (Pixtral) |
| `SEC_EVENT_TOKEN` | Token para autenticar eventos externos |
