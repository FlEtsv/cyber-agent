# Guía de usuario — CyberAgent iOS

App nativa para iPhone que conecta con el relay Cloud Run y actúa como cliente inteligente del agente de ciberseguridad.

---

## Requisitos

| Elemento | Requisito |
|----------|-----------|
| iOS | 17.0 o superior |
| Xcode | 17 (para compilar) |
| Apple Developer | Cuenta activa (para instalar en dispositivo) |
| PC CyberAgent | Corriendo con Ollama activo |
| Relay Cloud Run | Desplegado (ver `docs/CONNECTION_GUIDE.md`) |

---

## Pantallas y flujo

### 1. Login

Al abrir la app por primera vez verás la pantalla de login:

- **Email:** el mismo configurado en el relay (`RELAY_EMAIL`)
- **Contraseña:** la contraseña del relay
- **Código TOTP:** si el relay tiene TOTP activo (obligatorio por defecto desde RELAY-SEC-001), introduce el código de tu app de autenticación (Google Authenticator, Authy, etc.)

La app detecta automáticamente si hay conexión a internet:
- 🟢 **Relay en línea** → conecta al relay Cloud Run
- 🔴 **Modo local** → conecta directamente al PC por WiFi (misma red)

---

### 2. Chat (tab principal)

La pestaña de chat es el corazón de la app. Funciona igual que la interfaz web pero nativa.

**Enviar un mensaje:**
1. Escribe en el campo de texto inferior
2. Pulsa el botón de enviar (▶) o presiona Return

**Durante la respuesta del agente:**
- Verás las burbujas de texto aparecer en tiempo real (streaming)
- El indicador de actividad muestra que el agente está pensando

**Tarjetas de aprobación:**
Cuando el agente quiere usar una herramienta peligrosa, aparece una tarjeta de aprobación:

```
┌─────────────────────────────────────┐
│ 🛠 port_scan                         │
│ [network] [ALTO RIESGO]              │
│ host: "192.168.1.1"                  │
│ ports: "1-1024"                      │
│                                      │
│  ✅ Aprobar    ❌ Rechazar   ⏱ 60s  │
└─────────────────────────────────────┘
```

- **Aprobar:** el agente ejecuta la herramienta en el PC
- **Rechazar:** el agente cancela y busca otra forma
- **Timeout:** si no respondes en 60s, se rechaza automáticamente

**Herramientas bloqueadas en iPhone:**
Las siguientes herramientas nunca se ejecutan desde iPhone (solo desde el PC):
- `shell`, `write_file`, `kill_process`, `install_package`
- `registry_query`, `click_screen`, `type_text`, `hotkey`
- `credential_lookup`, `clipboard_write`

---

### 3. Dispositivos (tab)

Lista todos los dispositivos detectados por el iPhone:

**Bluetooth:**
- Botón "Escanear" → busca dispositivos BLE durante 10 segundos
- Lista con nombre, señal (dBm) y estado
- Pulsa en un dispositivo para conectar y leer sus servicios

**GPS:**
- Muestra tu posición actual en coordenadas y dirección (geocodificada)
- El agente incluye automáticamente tu posición en el contexto si está disponible

**Accesorios USB:**
- Lista de dispositivos MFi conectados (auriculares, cámaras, etc.)
- Se actualiza automáticamente cuando conectas o desconectas un accesorio

El agente tiene acceso a esta información y puede usarla en sus respuestas.

---

### 4. Ajustes (tab)

#### Conexión
- **URL del relay:** cambia el relay Cloud Run si usas un despliegue propio
- **IP del PC local:** la IP de tu PC en la red WiFi (para conexión directa)
- **Preferir red local:** cuando está activado, la app intenta conectar al PC directamente antes de usar el relay

#### Seguridad
- **Modo experto:** desactiva las tarjetas de aprobación para herramientas seguras (solo locales). Las herramientas peligrosas siguen requiriendo aprobación siempre.

#### Permisos por herramienta
- Lista todas las herramientas disponibles
- Por defecto: herramientas seguras = Auto, resto = Preguntar, peligrosas = Bloqueado
- Puedes cambiar el permiso de cada herramienta individualmente

#### Cerrar sesión
- Elimina el token de la Keychain
- La próxima apertura pedirá login de nuevo

---

## Modos de operación

### Modo Relay (normal — con internet)

```
iPhone → Cloud Run Relay → PC Windows → Ollama (Qwen2.5-32B)
```

El PC hace toda la inferencia. El iPhone solo muestra la conversación y gestiona aprobaciones.

### Modo Local (misma red WiFi)

```
iPhone → WiFi → PC Windows (8765) → Ollama (Qwen2.5-32B)
```

Más rápido y sin latencia del relay. Requiere estar en la misma red que el PC.

### Modo Offline (sin internet y sin PC)

```
iPhone → Mini LLM local (CoreML)
```

Si no hay ni relay ni PC accesible, la app activa el mini LLM local para respuestas básicas:
- Consulta de GPS, Bluetooth y accesorios USB
- Preguntas simples y contexto de dispositivos
- No tiene acceso a herramientas del PC

---

## Selector de dispositivo

La app puede cambiar automáticamente de modo según la tarea:

1. Envías un mensaje desde el iPhone
2. El agente determina si la tarea requiere herramientas del PC
3. Si está en modo offline, indica que la tarea necesita conexión
4. Si el relay está disponible, ejecuta en el PC

Para forzar un modo manualmente: ve a **Ajustes → Conexión → Preferir red local**.

---

## Comportamiento del agente

El agente actúa de forma autónoma:

- **Divide tareas complejas** en pasos verificables
- **Usa múltiples herramientas** de forma encadenada sin intervención manual
- **Resume el progreso** si una herramienta falla o necesita aprobación
- **Incluye contexto del dispositivo** automáticamente (GPS, BLE conectado, accesorios)
- **Adapta la respuesta** según si estás en iPhone o PC

### Ejemplos de tareas desde iPhone

| Tarea | Modo | Herramientas usadas |
|-------|------|---------------------|
| "¿Dónde estoy?" | Local/Offline | GPS |
| "¿Qué dispositivos BLE hay cerca?" | Local/Offline | BLE scan |
| "Escanea los puertos de mi red" | Relay/LAN | port_scan (en PC) |
| "Captura la pantalla del PC" | Relay/LAN | screenshot_pc (en PC) |
| "Busca en Google sobre este CVE" | Relay/LAN | web_search (en PC) |

---

## Instalar en Xcode

```bash
# En Mac con Xcode 17:
cd /ruta/al/proyecto/ios
open Package.swift   # o crear el .xcodeproj apuntando a esta carpeta

# Seleccionar target: iPhone real (requiere Apple Developer)
# Product → Run (⌘R)
```

### Configuración del Bundle ID
En el target del proyecto Xcode:
- **Bundle Identifier:** `com.tudominio.cyberagent`
- **Signing:** tu equipo de desarrollo
- **Deployment Target:** iOS 17.0

### Permisos que requiere Xcode
La app pide automáticamente los permisos en runtime:
- Bluetooth → primera vez que se abre la pestaña Dispositivos
- Ubicación → primera vez que se activa el GPS
- Red local → primera vez que intenta conexión LAN

---

## Solución de problemas

| Problema | Causa probable | Solución |
|----------|---------------|----------|
| "Credenciales incorrectas" | TOTP incorrecto o email mal | Verifica el código TOTP en tu autenticador |
| "Reconectando..." | El relay/PC se desconectó | La app se reconecta sola; espera unos segundos |
| "PC no conectado" | CyberAgent no está corriendo en el PC | Abre CyberAgent en el PC |
| Tarjetas de aprobación no responden | Timer expirado | Rechaza y vuelve a pedir la herramienta |
| Mini LLM no disponible | Modelo CoreML no añadido en Xcode | Normal — usa el fallback basado en reglas |
| GPS no activo | Permiso denegado | Ajustes iPhone → Privacidad → Ubicación → CyberAgent |
| BLE no escanea | Permiso denegado | Ajustes iPhone → Privacidad → Bluetooth → CyberAgent |

---

## Arquitectura técnica

```
CyberAgent iOS
├── Auth/           AuthManager (JWT + Keychain)
├── Relay/          RelayManager (URLSessionWebSocketTask, reconexión)
├── Chat/           ChatViewModel (lógica agente), ChatView, ToolApprovalCard
├── Devices/        BLEManager, GPSManager, AccessoryDetector, DeviceManager
├── LocalLLM/       LocalLLMManager (CoreML), OfflineAgentRunner
├── Network/        NetworkMonitor (NWPathMonitor), ConnectionResolver
├── Permissions/    PermissionManager, MOBILE_SAFE_TOOLS, MOBILE_BLOCKED_TOOLS
├── Models/         ChatMessage, AgentEvent, ToolPayload, ...
└── Utils/          Constants, KeychainHelper, Theme
```

El relay PC sigue siendo el punto de control — el iPhone actúa como cliente inteligente que:
1. Conecta por WebSocket al relay (o directamente al PC)
2. Envía mensajes con contexto del dispositivo (GPS, BLE, accesorios)
3. Muestra la respuesta en streaming
4. Gestiona aprobaciones de herramientas con timeout
5. Puede responder localmente con el mini LLM si no hay conexión
