# Guía de usuario — CyberAgent

CyberAgent es un asistente de IA con capacidades de seguridad, análisis y control del PC. Se ejecuta en tu Windows 11 con un modelo LLM local (Ollama) y es accesible desde el escritorio, la red local, iPhone o cualquier navegador via Cloud Run.

---

## Formas de acceso

### 1. Escritorio (GUI nativa — Windows)
La forma más completa. Inicia el agente desde el escritorio:
- Barra de tareas → ícono de CyberAgent
- O ejecuta: `pythonw main.py` desde `C:\Users\steve\cyber-llm\agent-native\`

Características:
- Chat principal con el agente
- Panel terminal integrado
- Panel de herramientas activas
- Estado de conexión en tiempo real (relay/Ollama/GPU)

### 2. Navegador local (PWA — misma red)
Accede desde cualquier dispositivo en tu red local:
```
http://192.168.18.240:8765
```
Puedes instalarlo como PWA en Chrome/Edge para tenerlo en la barra de tareas del navegador.

### 3. Cloud Run relay (acceso remoto — iPhone/cualquier lugar)
Accede desde cualquier lugar a través del relay seguro:
```
https://cyberagent-relay-819820880956.us-central1.run.app
```
Desde iPhone: abre la URL en Safari → "Añadir a la pantalla de inicio" para instalar como app.

El relay muestra si el PC está conectado (`PC online ✓`) o no (`PC offline`). Si el PC está offline, el chat conecta igualmente pero las herramientas locales no están disponibles.

---

## Uso del chat

### Enviar un mensaje
Escribe tu mensaje en el campo de texto y pulsa Enter o el botón de envío. El agente:
1. Analiza tu mensaje
2. Decide qué herramientas usar (si necesita alguna)
3. Ejecuta herramientas con tu aprobación cuando son de riesgo alto
4. Responde con el resultado

### Modelos de IA disponibles

CyberAgent usa dos modelos según la complejidad de la tarea:

| Modelo | Cuándo se usa | Velocidad |
|--------|--------------|-----------|
| **Rápido** (cyberagent-original) | Chat, consultas, tareas simples, información del sistema | Rápido (~2-5s) |
| **Potente** | Análisis profundos, arquitectura de sistemas, exploits complejos, refactorizaciones | Más lento (10-30s) |

El agente selecciona automáticamente el modelo apropiado según la complejidad de tu petición. No necesitas especificarlo manualmente.

### Tipos de tareas que puedes pedir

**Seguridad y hacking (CTF / auditoría propia):**
- "Escanea los puertos abiertos de 192.168.1.1"
- "Haz un pentest completo a mi servidor web"
- "Analiza este binario sospechoso y dime si es malware"
- "¿Qué mecanismos de persistencia hay en este sistema?"

**Control del PC:**
- "Captura una pantalla y dime qué programas están abiertos"
- "Abre Chrome y ve a GitHub"
- "Extrae el texto de la ventana activa"
- "Cierra todos los procesos de Excel"

**Desarrollo y análisis:**
- "Analiza este código Python y dime si tiene vulnerabilidades"
- "Busca todos los archivos .log modificados hoy en C:/"
- "Ejecuta este script y muéstrame el resultado"

**Información del sistema:**
- "¿Cuánta RAM estoy usando?"
- "Muéstrame el uso de GPU en tiempo real"
- "¿Qué procesos consumen más CPU?"

**Internet y búsquedas:**
- "Busca los CVE más recientes de Apache"
- "Descarga y resume este PDF"
- "Comprueba si este dominio tiene SPF configurado"

---

## Tarjetas de aprobación de herramientas

Cuando el agente quiere ejecutar una **herramienta de riesgo alto** (como ejecutar un comando shell, hacer click en pantalla, o escanear puertos), aparece una tarjeta de aprobación:

```
┌─────────────────────────────────────┐
│ ⚡ shell                    [ALTO] │
│ comando: Get-Process | Sort CPU    │
│                                    │
│   [Aprobar]        [Rechazar]      │
└─────────────────────────────────────┘
```

- **Aprobar** → se ejecuta la herramienta
- **Rechazar** → el agente busca una alternativa o te informa

En el escritorio puedes configurar "modo confianza" para aprobar automáticamente categorías específicas.

---

## Filas de acción (action rows)

Durante la ejecución, el chat muestra filas de acción con:
- Ícono de la categoría (red, web, archivos, etc.)
- Nombre de la herramienta
- Estado (ejecutando / completado / error)
- Preview del resultado (sin secretos ni tokens — redactados automáticamente)

---

## Reportes de sesión

Puedes exportar un reporte de la sesión actual en cualquier momento:
- En el chat → botón **"Reporte"** en la cabecera
- El reporte incluye: mensajes, herramientas usadas, errores, duración y eventos de conexión
- Se descarga como JSON o HTML
- Los valores sensibles (tokens, contraseñas) se redactan automáticamente antes de exportar

---

## Base de conocimiento (RAG)

El agente tiene una base de conocimiento interna que puede consultar y ampliar:
- **Consultar:** "¿Recuerdas cómo configuramos el relay?"
- **Ampliar:** "Guarda esto para que lo recuerdes: [información técnica]"

La base de conocimiento se actualiza automáticamente cada 30 minutos con temas técnicos de ciberseguridad (DuckDuckGo → ChromaDB).

---

## Seguridad y privacidad

- **Todo el procesamiento es local**: el modelo LLM (Ollama) corre en tu PC, sin enviar datos a terceros.
- **El relay es solo un puente**: el Cloud Run relay no almacena tus mensajes, solo retransmite la conexión WebSocket.
- **Redacción automática de secretos**: los logs y reportes redactan automáticamente passwords, tokens, API keys, JWTs y TOTPs.
- **Herramientas de alto riesgo requieren aprobación**: nunca se ejecutan automáticamente sin tu confirmación.

---

## Cuando el PC está offline

Si accedes desde el iPhone o relay y el PC está desconectado:
- El banner muestra "PC offline"
- El chat sigue conectado al relay pero las herramientas locales no están disponibles
- El PC reconecta automáticamente cuando vuelve a estar online (backoff exponencial)

---

## Resolución de problemas rápida

| Problema | Solución |
|----------|----------|
| "reconectando..." en bucle | Verifica que Ollama está corriendo: `curl http://localhost:11434/api/tags` |
| La GUI no abre | Ejecuta `main.py` desde `.venv\Scripts\pythonw.exe main.py` en el directorio del proyecto |
| "PC offline" en el relay | El agente no está corriendo en el PC. Inicia `pythonw main.py` |
| Error de autenticación | Revisa `.env` y `data/.env` para `RELAY_URL` y `RELAY_HOST_SECRET` |
| GPU no detectada | Reinicia Ollama: `ollama serve` |

Para diagnóstico detallado: solicita al agente "muéstrame el reporte de sesión completo".
