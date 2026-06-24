# Manual de Herramientas — CyberAgent

Manual completo de cada herramienta disponible en CyberAgent. Cada herramienta incluye categoría, nivel de riesgo, descripción técnica, cuándo usarla, y ejemplo de uso.

---

## Categorías y niveles de riesgo

| Categoría | Riesgo | Descripción |
|-----------|--------|-------------|
| `core` | bajo/alto | Ejecución básica y lectura/escritura — incluye shell y run_python (alto) |
| `web` | bajo/alto | Fetch de URLs y auditoría web — dir_bruteforce requiere autorización |
| `files` | bajo | Búsqueda y análisis de archivos locales |
| `system` | bajo/alto | Estado del SO; kill/install son de riesgo alto |
| `desktop` | alto | Control visual del escritorio Windows |
| `network` | alto | Reconocimiento de red (requiere autorización sobre el objetivo) |
| `forensics` | bajo | Análisis local de binarios y artefactos de Windows |
| `hacking` | alto | Combinación ofensiva/defensiva completa para pentesting y CTF |
| `encode` | bajo | Transformaciones de datos sin efecto en el sistema |
| `rag` | bajo | Base de conocimiento interna del agente |
| `self` | alto | Auto-inspección y reinicio del agente |
| `mobile` | alto | Control de dispositivos Android/iOS conectados |

---

## Herramientas core

### `shell`
- **Riesgo:** alto — requiere aprobación  
- **Descripción:** Ejecuta comandos en PowerShell (Windows), bash (WSL Ubuntu) o cmd.  
- **Cuándo usar:** Para cualquier comando que no tenga herramienta dedicada — instalar software con scripts, diagnósticos, automatización.  
- **Ejemplo:** `shell(command="Get-Process | Sort-Object CPU -Descending | Select-Object -First 5", shell_type="powershell")`  
- **Nota:** Úsalo con `shell_type` explícito. Timeout default 60s.

### `read_file`
- **Riesgo:** bajo  
- **Descripción:** Lee el contenido de un archivo del sistema. Soporta offset y limit de líneas.  
- **Cuándo usar:** Para leer logs, configs, código fuente, archivos de texto.  
- **Ejemplo:** `read_file(path="C:/Users/user/agent.log", offset=0, limit=50)`

### `write_file`
- **Riesgo:** alto — requiere aprobación  
- **Descripción:** Escribe o sobreescribe un archivo. Con `append=true` añade al final.  
- **Cuándo usar:** Para crear archivos de configuración, guardar resultados, editar scripts.  
- **Ejemplo:** `write_file(path="C:/temp/resultado.txt", content="Datos...", append=false)`

### `run_python`
- **Riesgo:** alto — requiere aprobación  
- **Descripción:** Ejecuta código Python arbitrario y devuelve stdout/stderr.  
- **Cuándo usar:** Para análisis de datos, cálculos, parsing, tareas que requieren lógica compleja.  
- **Ejemplo:** `run_python(code="import json; data={'x': 42}; print(json.dumps(data))")`

---

## Herramientas web

### `web_search`
- **Riesgo:** bajo  
- **Descripción:** Busca información actualizada en internet via DuckDuckGo. Devuelve títulos, snippets y URLs.  
- **Cuándo usar:** Para noticias, CVEs recientes, documentación, artículos técnicos.  
- **Ejemplo:** `web_search(query="CVE-2024-12345 exploit", max_results=5)`

### `web_fetch`
- **Riesgo:** bajo (solo URLs externas autorizadas)  
- **Descripción:** Descarga el contenido de una URL y extrae el texto. Bloquea loopback/IPs privadas.  
- **Cuándo usar:** Para leer páginas web, documentación online, APIs sin auth.  
- **Ejemplo:** `web_fetch(url="https://nvd.nist.gov/vuln/detail/CVE-2024-12345")`

### `http_request`
- **Riesgo:** bajo/alto según destino  
- **Descripción:** Petición HTTP completa (GET/POST/PUT/DELETE/PATCH). Control total de headers y body.  
- **Cuándo usar:** Para APIs REST con autenticación, webhooks, scraping con headers custom.  
- **Ejemplo:** `http_request(url="https://api.example.com/v1/users", method="POST", headers={"Authorization": "Bearer TOKEN"}, body='{"name": "test"}')`

### `ssl_info`
- **Riesgo:** bajo  
- **Descripción:** Analiza certificado SSL/TLS: versión TLS, cipher, validez, emisor, SANs, expiración.  
- **Cuándo usar:** Para auditar el certificado de un servidor, detectar expiración o configuración débil.  
- **Ejemplo:** `ssl_info(host="example.com", port=443)`

### `http_headers_check`
- **Riesgo:** bajo  
- **Descripción:** Analiza cabeceras HTTP de seguridad: HSTS, CSP, X-Frame-Options, CORS. Devuelve score.  
- **Cuándo usar:** Auditoría básica de seguridad de un servidor web.  
- **Ejemplo:** `http_headers_check(url="https://example.com")`

### `web_crawl`
- **Riesgo:** alto — solo en activos propios o autorizados  
- **Descripción:** Rastrea una web y extrae todos los enlaces (internos y externos).  
- **Cuándo usar:** Para mapear superficie de ataque, descubrir endpoints ocultos.  
- **Ejemplo:** `web_crawl(url="https://myapp.com", depth=2, max_links=100)`

### `dir_bruteforce`
- **Riesgo:** alto — solo en activos propios o autorizados  
- **Descripción:** Enumera directorios y archivos web probando paths comunes (admin, .git, .env, api...).  
- **Cuándo usar:** Para descubrir recursos no listados en un servidor web. Requiere autorización.  
- **Ejemplo:** `dir_bruteforce(url="http://target.com", wordlist="common", timeout=5, max_workers=20)`

---

## Herramientas de archivos

### `list_directory`
- **Riesgo:** bajo  
- **Descripción:** Lista el contenido de un directorio con tamaños y fechas.  
- **Ejemplo:** `list_directory(path="C:/Users/user/Documents", recursive=false)`

### `search_files`
- **Riesgo:** bajo  
- **Descripción:** Busca archivos por nombre, extensión o contenido (glob + texto interior).  
- **Ejemplo:** `search_files(path="C:/", pattern="*.log", content="error", recursive=true, max_results=20)`

### `grep_files`
- **Riesgo:** bajo  
- **Descripción:** Busca patrones regex en archivos de un directorio con contexto de líneas.  
- **Cuándo usar:** Más potente que `search_files` cuando necesitas regex y contexto.  
- **Ejemplo:** `grep_files(directory="C:/app", pattern="password\s*=", file_glob="*.py", context_lines=3)`

### `diff_files`
- **Riesgo:** bajo  
- **Descripción:** Compara dos archivos y muestra diferencias línea a línea.  
- **Ejemplo:** `diff_files(file_a="config.old.json", file_b="config.json")`

### `hash_file`
- **Riesgo:** bajo  
- **Descripción:** Calcula MD5/SHA256/SHA1/SHA512 de un archivo.  
- **Ejemplo:** `hash_file(path="setup.exe", algorithm="sha256")`

### `file_metadata`
- **Riesgo:** bajo  
- **Descripción:** Metadatos completos: tamaño, fechas, tipo por magic bytes, hashes, firma digital.  
- **Ejemplo:** `file_metadata(path="suspicious.exe")`

---

## Herramientas de sistema

### `list_processes`
- **Riesgo:** bajo  
- **Descripción:** Lista procesos con CPU y memoria. Ordenable por memoria, CPU, nombre o PID.  
- **Ejemplo:** `list_processes(sort_by="cpu")`

### `system_info`
- **Riesgo:** bajo  
- **Descripción:** Información completa: OS, hardware, red, procesos, disco.  
- **Ejemplo:** `system_info(section="hardware")`

### `memory_info`
- **Riesgo:** bajo  
- **Descripción:** RAM total, disponible, top N procesos por consumo.  
- **Ejemplo:** `memory_info(top_n=10)`

### `gpu_info`
- **Riesgo:** bajo  
- **Descripción:** Uso de GPU, VRAM, temperatura, procesos activos en GPU.  
- **Ejemplo:** `gpu_info()`

### `network_info`
- **Riesgo:** bajo  
- **Descripción:** Interfaces de red, IPs, conexiones activas, tabla de rutas, DNS.  
- **Ejemplo:** `network_info(section="connections")`

### `env_vars`
- **Riesgo:** alto (set/delete)  
- **Descripción:** Lee o escribe variables de entorno.  
- **Ejemplo:** `env_vars(action="get", name="PATH")` / `env_vars(action="set", name="DEBUG", value="1", scope="process")`

### `kill_process`
- **Riesgo:** alto — requiere aprobación  
- **Descripción:** Termina un proceso por nombre o PID.  
- **Ejemplo:** `kill_process(name="chrome.exe", force=true)`

### `install_package`
- **Riesgo:** alto — requiere aprobación  
- **Descripción:** Instala paquetes con pip, winget, npm, choco o apt (WSL).  
- **Ejemplo:** `install_package(package="nmap", manager="winget")`

### `uninstall_package`
- **Riesgo:** alto — requiere aprobación  
- **Descripción:** Desinstala un paquete.  
- **Ejemplo:** `uninstall_package(package="old-software", manager="winget")`

---

## Herramientas de desktop (control del PC)

> Todas requieren aprobación explícita del usuario.

### `screenshot_pc`
- **Descripción:** Captura la pantalla del monitor indicado.  
- **Ejemplo:** `screenshot_pc(monitor=0)`

### `list_monitors`
- **Descripción:** Lista todas las pantallas con posición, resolución, escala y cuál es la principal.  
- **Ejemplo:** `list_monitors()`

### `active_window`
- **Descripción:** Devuelve la ventana activa: handle, título, proceso, PID y rectángulo.  
- **Ejemplo:** `active_window()`

### `list_windows`
- **Descripción:** Lista ventanas visibles del escritorio. Filtra por título o proceso.  
- **Ejemplo:** `list_windows(title_filter="Chrome", limit=20)`

### `focus_window`
- **Descripción:** Trae una ventana al frente por hwnd, título parcial o PID.  
- **Ejemplo:** `focus_window(title="Notepad")`

### `click_screen`
- **Descripción:** Hace click en coordenadas absolutas de pantalla.  
- **Ejemplo:** `click_screen(x=960, y=540, button="left", clicks=1)`

### `type_text`
- **Descripción:** Escribe texto Unicode en el campo activo de Windows.  
- **Ejemplo:** `type_text(text="Hola mundo", interval_ms=0)`

### `hotkey`
- **Descripción:** Envía combinación de teclas.  
- **Ejemplo:** `hotkey(keys=["ctrl", "c"])` / `hotkey(keys=["alt", "F4"])`

### `ocr_screen`
- **Descripción:** Captura pantalla y extrae texto visible con OCR (requiere Tesseract instalado).  
- **Ejemplo:** `ocr_screen(monitor=0)` / `ocr_screen(x=100, y=200, width=400, height=150)`

### `ui_tree`
- **Descripción:** Inspecciona controles de ventana via Windows UI Automation. Útil antes de hacer click.  
- **Ejemplo:** `ui_tree(depth=3, limit=100)`

### `fill_form`
- **Descripción:** Rellena un formulario con acciones secuenciales (click, type, hotkey, wait).  
- **Ejemplo:** `fill_form(title="Login", actions=[{"click": {"x": 400, "y": 300}}, {"type": {"text": "usuario"}}, {"hotkey": {"keys": ["tab"]}}, {"type": {"text": "contraseña"}}])`

### `credential_lookup`
- **Descripción:** Consulta credenciales guardadas en Windows Credential Manager y navegadores Chromium.  
- **Ejemplo:** `credential_lookup(source="windows", query="github", reveal=false)`

### `clipboard_read`
- **Descripción:** Lee el portapapeles de Windows.  
- **Ejemplo:** `clipboard_read()`

### `clipboard_write`
- **Descripción:** Escribe texto en el portapapeles.  
- **Ejemplo:** `clipboard_write(text="texto a copiar")`

### `open_browser`
- **Descripción:** Abre una URL en el navegador predeterminado.  
- **Ejemplo:** `open_browser(url="https://example.com")`

### `windows_notify`
- **Descripción:** Envía notificación toast de Windows al usuario.  
- **Ejemplo:** `windows_notify(title="CyberAgent", message="Tarea completada")`

---

## Herramientas de red (reconocimiento)

> Todas requieren autorización sobre el objetivo.

### `port_scan`
- **Descripción:** Escanea puertos TCP. Sin nmap, socket-based.  
- **Ejemplo:** `port_scan(host="192.168.1.1", ports="1-1024", timeout=0.5)`

### `dns_lookup`
- **Descripción:** Consultas DNS: A, AAAA, MX, TXT, NS, CNAME, SOA, PTR.  
- **Ejemplo:** `dns_lookup(hostname="example.com", record_type="MX")`

### `whois_lookup`
- **Descripción:** WHOIS de un dominio: registrar, fechas, name servers.  
- **Ejemplo:** `whois_lookup(domain="example.com")`

### `traceroute`
- **Descripción:** Ruta de red hasta un host (salto a salto).  
- **Ejemplo:** `traceroute(host="8.8.8.8", max_hops=20)`

### `banner_grab`
- **Descripción:** Captura el banner de un servicio TCP (versión de software).  
- **Ejemplo:** `banner_grab(host="192.168.1.10", port=22, timeout=3)`

### `ping_sweep`
- **Descripción:** Descubre hosts activos en una subred (CIDR o rango). Max 256 hosts.  
- **Ejemplo:** `ping_sweep(network="192.168.1.0/24", timeout_ms=500)`

### `arp_cache`
- **Descripción:** Tabla ARP local: IPs y MACs de la red local.  
- **Ejemplo:** `arp_cache()`

### `network_connections`
- **Descripción:** Conexiones TCP activas con proceso propietario.  
- **Ejemplo:** `network_connections(state="established")`

---

## Herramientas forenses

### `strings_extract`
- **Descripción:** Extrae strings ASCII/Unicode de un binario. Esencial para análisis de malware e IOCs.  
- **Ejemplo:** `strings_extract(path="malware.exe", min_length=6)`

### `hex_dump`
- **Descripción:** Volcado hexadecimal de un archivo o sección.  
- **Ejemplo:** `hex_dump(path="file.bin", offset=0, length=512)`

### `file_entropy`
- **Descripción:** Entropía de Shannon por secciones. >7.2 indica packing/cifrado.  
- **Ejemplo:** `file_entropy(path="suspicious.exe")`

### `pe_info`
- **Descripción:** Cabecera PE de ejecutables Windows: secciones, imports, exports, timestamp.  
- **Ejemplo:** `pe_info(path="target.exe")`

### `registry_query`
- **Descripción:** Lee claves/valores del registro de Windows. Útil para auditoría y malware analysis.  
- **Ejemplo:** `registry_query(key="HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run")`

### `list_services`
- **Descripción:** Lista servicios de Windows con estado y tipo de inicio.  
- **Ejemplo:** `list_services(state="running", name_filter="sql")`

### `check_persistence`
- **Descripción:** Audita mecanismos de persistencia: registry autoruns, inicio, tareas, servicios.  
- **Ejemplo:** `check_persistence()`

### `process_tree`
- **Descripción:** Árbol jerárquico de procesos. Detecta procesos inyectados con parent incorrecto.  
- **Ejemplo:** `process_tree()`

### `process_info`
- **Descripción:** Información detallada de un proceso: cmdline, módulos, handles, usuario.  
- **Ejemplo:** `process_info(pid=1234)` / `process_info(name="svchost.exe")`

---

## Herramientas de codificación

### `encode_decode`
- **Riesgo:** bajo  
- **Descripción:** Codifica/decodifica: base64, URL encoding, hex, rot13.  
- **Ejemplo:** `encode_decode(text="Hello World", operation="base64_encode")`  
- **Operaciones disponibles:** `base64_encode`, `base64_decode`, `url_encode`, `url_decode`, `hex_encode`, `hex_decode`, `rot13`

---

## Herramientas RAG (base de conocimiento)

### `rag_search`
- **Riesgo:** bajo  
- **Descripción:** Busca semánticamente en la base de conocimiento interna del agente (ChromaDB).  
- **Ejemplo:** `rag_search(query="cómo configurar Cloudflare Tunnel", n_results=3)`

### `rag_add`
- **Riesgo:** bajo  
- **Descripción:** Añade nueva información a la base de conocimiento. Úsala para aprendizaje activo.  
- **Ejemplo:** `rag_add(title="CVE-2024-12345 workaround", content="Parchear con...", tags=["security", "cve"], platform="windows")`

---

## Herramientas de auto-conciencia

### `list_self_files`
- **Riesgo:** bajo  
- **Descripción:** Lista todos los archivos del proyecto CyberAgent con rutas, tamaños y fechas.  
- **Ejemplo:** `list_self_files()`

### `syntax_check`
- **Riesgo:** bajo  
- **Descripción:** Verifica la sintaxis Python de un archivo antes de aplicar cambios.  
- **Ejemplo:** `syntax_check(path="app/tools.py")`

### `restart_self`
- **Riesgo:** alto — requiere aprobación  
- **Descripción:** Reinicia CyberAgent para aplicar cambios en el código fuente. La conversación actual termina.  
- **Uso correcto:** Siempre ejecutar `syntax_check()` antes de `restart_self()`.  
- **Ejemplo:** `restart_self()`

---

## Flujo de trabajo autorizado para seguridad

Para tareas de hacking/pentesting, seguir esta progresión:

1. **Reconocimiento pasivo:** `web_search`, `dns_lookup`, `whois_lookup`
2. **Auditoría web:** `ssl_info`, `http_headers_check`, `web_crawl`
3. **Reconocimiento activo** _(solo activos propios o autorizados):_ `port_scan`, `banner_grab`, `dir_bruteforce`, `ping_sweep`
4. **Análisis forense local:** `strings_extract`, `file_entropy`, `pe_info`, `registry_query`, `list_services`, `check_persistence`
5. **Informe:** Resumir evidencias, comandos, resultados y pasos siguientes en el chat

> **Nota de ética:** Las herramientas de red activa (`port_scan`, `dir_bruteforce`, `ping_sweep`, `banner_grab`) solo deben usarse sobre activos que el usuario posee o sobre los que tiene autorización escrita. CyberAgent no da soporte a actividad no autorizada.

---

## Gestión de permisos en la UI

Las herramientas de riesgo alto muestran una **tarjeta de aprobación** en el chat antes de ejecutarse. El usuario puede:
- **Aprobar** — la herramienta se ejecuta
- **Rechazar** — la herramienta no se ejecuta; el agente busca alternativa

En la web y relay, las filas de acción muestran categoría, riesgo y un preview del resultado redactado automáticamente (sin secretos ni tokens).
