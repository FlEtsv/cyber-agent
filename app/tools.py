import subprocess, os, json, shutil, sys, hashlib, difflib, fnmatch, time, threading
import urllib.parse, base64, codecs, glob
from datetime import datetime
from app.mobile_tools import (MOBILE_TOOLS_SCHEMA, MOBILE_DANGEROUS,
                               execute_mobile_tool)

# ── TTL cache para herramientas read-only frecuentes (PERF-001) ───────────────
_cache_store: dict[str, tuple[float, dict]] = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 30  # segundos

_CACHEABLE_TOOLS = frozenset({"system_info", "gpu_info", "memory_info"})


def _cache_key(name: str, args: dict) -> str:
    return name + "|" + json.dumps(args, sort_keys=True)


def _cache_get(key: str) -> dict | None:
    with _cache_lock:
        entry = _cache_store.get(key)
        if entry and time.time() - entry[0] < _CACHE_TTL:
            return entry[1]
        return None


def _cache_set(key: str, result: dict):
    with _cache_lock:
        _cache_store[key] = (time.time(), result)

def _sa_module():
    """Lazy import de self_awareness para evitar circular imports."""
    from app.consciousness import self_awareness as _sa
    return type("_SA", (), {
        "list_self_files": staticmethod(_sa._list_self_files),
        "syntax_check":    staticmethod(_sa._syntax_check),
        "restart_self":    staticmethod(_sa._restart_self),
    })()

TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "shell",
        "description": "Ejecuta un comando en PowerShell (Windows) o bash (WSL Ubuntu). "
                       "Usa shell_type='powershell' para comandos Windows y 'bash' para Linux.",
        "parameters": {"type": "object", "properties": {
            "command":    {"type": "string", "description": "Comando a ejecutar"},
            "shell_type": {"type": "string", "enum": ["powershell", "bash", "cmd"],
                           "description": "Shell: 'powershell' (default), 'bash' (WSL), 'cmd'"},
            "timeout":    {"type": "integer", "description": "Timeout en segundos (default 60)"},
        }, "required": ["command"]}
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Lee el contenido de un archivo del sistema.",
        "parameters": {"type": "object", "properties": {
            "path":   {"type": "string", "description": "Ruta del archivo"},
            "offset": {"type": "integer", "description": "Línea desde donde empezar (default 0)"},
            "limit":  {"type": "integer", "description": "Máximo de líneas a leer (default todas)"},
        }, "required": ["path"]}
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Escribe o sobreescribe un archivo. Crea directorios intermedios si no existen.",
        "parameters": {"type": "object", "properties": {
            "path":    {"type": "string", "description": "Ruta del archivo"},
            "content": {"type": "string", "description": "Contenido a escribir"},
            "append":  {"type": "boolean", "description": "Si true, añade al final en vez de sobreescribir"},
        }, "required": ["path", "content"]}
    }},
    {"type": "function", "function": {
        "name": "list_directory",
        "description": "Lista el contenido de un directorio con tamaños y fechas.",
        "parameters": {"type": "object", "properties": {
            "path":      {"type": "string", "description": "Ruta del directorio"},
            "recursive": {"type": "boolean", "description": "Listar recursivamente"},
        }, "required": ["path"]}
    }},
    {"type": "function", "function": {
        "name": "web_fetch",
        "description": "Descarga el contenido de una URL y devuelve el texto extraído.",
        "parameters": {"type": "object", "properties": {
            "url":     {"type": "string", "description": "URL a descargar"},
            "headers": {"type": "object", "description": "Headers HTTP adicionales"},
        }, "required": ["url"]}
    }},
    {"type": "function", "function": {
        "name": "run_python",
        "description": "Ejecuta código Python arbitrario y devuelve stdout/stderr. "
                       "Úsalo para análisis de datos, cálculos, o tareas que requieren lógica compleja.",
        "parameters": {"type": "object", "properties": {
            "code":    {"type": "string", "description": "Código Python a ejecutar"},
            "timeout": {"type": "integer", "description": "Timeout en segundos (default 30)"},
        }, "required": ["code"]}
    }},
    {"type": "function", "function": {
        "name": "list_processes",
        "description": "Lista procesos en ejecución con uso de CPU y memoria.",
        "parameters": {"type": "object", "properties": {
            "filter_name": {"type": "string", "description": "Filtrar por nombre de proceso (opcional)"},
            "sort_by":     {"type": "string", "enum": ["memory", "cpu", "name", "pid"],
                           "description": "Ordenar por (default: memory)"},
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "install_package",
        "description": "Instala un paquete de software usando el gestor indicado: "
                       "pip (Python), winget (Windows apps), npm (Node.js), choco (Chocolatey), apt (WSL/Linux).",
        "parameters": {"type": "object", "properties": {
            "package": {"type": "string", "description": "Nombre del paquete a instalar"},
            "manager": {"type": "string", "enum": ["pip", "winget", "npm", "choco", "apt"],
                       "description": "Gestor de paquetes"},
            "version": {"type": "string", "description": "Versión específica (opcional)"},
        }, "required": ["package", "manager"]}
    }},
    {"type": "function", "function": {
        "name": "uninstall_package",
        "description": "Desinstala un paquete usando el gestor indicado.",
        "parameters": {"type": "object", "properties": {
            "package": {"type": "string", "description": "Nombre del paquete a desinstalar"},
            "manager": {"type": "string", "enum": ["pip", "winget", "npm", "choco", "apt"],
                       "description": "Gestor de paquetes"},
        }, "required": ["package", "manager"]}
    }},
    {"type": "function", "function": {
        "name": "system_info",
        "description": "Obtiene información completa del sistema: OS, hardware, red, procesos, espacio en disco.",
        "parameters": {"type": "object", "properties": {
            "section": {"type": "string",
                       "enum": ["all", "os", "hardware", "network", "processes", "disk"],
                       "description": "Sección de información (default: all)"},
        }, "required": []}
    }},
    # ── Superagent tools ───────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "screenshot_pc",
        "description": "Captura la pantalla del PC. Útil para ver el estado actual del escritorio, "
                       "depurar errores visuales o analizar lo que está en pantalla.",
        "parameters": {"type": "object", "properties": {
            "monitor": {"type": "integer", "description": "Índice del monitor (0=principal, default 0)"},
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "list_monitors",
        "description": "Lista pantallas conectadas con posicion, resolucion, area de trabajo, primario y escala si Windows la expone.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
        "name": "active_window",
        "description": "Devuelve la ventana activa: handle, titulo, proceso, PID y rectangulo.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
        "name": "list_windows",
        "description": "Lista ventanas visibles del escritorio con titulo, PID, proceso, posicion y tamano.",
        "parameters": {"type": "object", "properties": {
            "title_filter": {"type": "string", "description": "Filtro opcional por titulo"},
            "process_filter": {"type": "string", "description": "Filtro opcional por nombre de proceso"},
            "limit": {"type": "integer", "description": "Maximo de ventanas (default 80)"}
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "focus_window",
        "description": "Trae una ventana al frente por hwnd, titulo parcial o PID.",
        "parameters": {"type": "object", "properties": {
            "hwnd": {"type": "integer", "description": "Handle de ventana"},
            "title": {"type": "string", "description": "Texto parcial del titulo"},
            "pid": {"type": "integer", "description": "PID del proceso"}
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "click_screen",
        "description": "Hace click en coordenadas absolutas de pantalla.",
        "parameters": {"type": "object", "properties": {
            "x": {"type": "integer"},
            "y": {"type": "integer"},
            "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Boton (default left)"},
            "clicks": {"type": "integer", "description": "Numero de clicks (default 1)"}
        }, "required": ["x", "y"]}
    }},
    {"type": "function", "function": {
        "name": "type_text",
        "description": "Escribe texto Unicode en el campo activo de Windows.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string"},
            "interval_ms": {"type": "integer", "description": "Pausa entre caracteres (default 0)"}
        }, "required": ["text"]}
    }},
    {"type": "function", "function": {
        "name": "hotkey",
        "description": "Envia una combinacion de teclas, por ejemplo ['ctrl','l'], ['tab'], ['enter'].",
        "parameters": {"type": "object", "properties": {
            "keys": {"type": "array", "items": {"type": "string"}}
        }, "required": ["keys"]}
    }},
    {"type": "function", "function": {
        "name": "ocr_screen",
        "description": "Captura pantalla y extrae texto visible con OCR si pytesseract/tesseract estan disponibles.",
        "parameters": {"type": "object", "properties": {
            "monitor": {"type": "integer", "description": "Monitor 0=principal"},
            "x": {"type": "integer", "description": "Recorte X opcional"},
            "y": {"type": "integer", "description": "Recorte Y opcional"},
            "width": {"type": "integer", "description": "Ancho de recorte opcional"},
            "height": {"type": "integer", "description": "Alto de recorte opcional"}
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "ui_tree",
        "description": "Inspecciona controles de la ventana activa o de una ventana por hwnd usando Windows UI Automation.",
        "parameters": {"type": "object", "properties": {
            "hwnd": {"type": "integer", "description": "Handle de ventana; si se omite usa ventana activa"},
            "depth": {"type": "integer", "description": "Profundidad maxima (default 2)"},
            "limit": {"type": "integer", "description": "Maximo de nodos (default 120)"}
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "fill_form",
        "description": "Rellena un formulario combinando focus, clicks, texto y hotkeys. Acepta acciones secuenciales.",
        "parameters": {"type": "object", "properties": {
            "hwnd": {"type": "integer", "description": "Ventana a enfocar antes de empezar"},
            "title": {"type": "string", "description": "Titulo parcial de ventana a enfocar"},
            "actions": {"type": "array", "items": {"type": "object"}, "description": "Acciones: click{x,y}, type{text}, hotkey{keys}, wait{ms}"}
        }, "required": ["actions"]}
    }},
    {"type": "function", "function": {
        "name": "credential_lookup",
        "description": "Consulta credenciales guardadas de la sesion actual en Windows Credential Manager y navegadores Chromium. reveal=true intenta devolver secretos cuando DPAPI lo permite.",
        "parameters": {"type": "object", "properties": {
            "source": {"type": "string", "enum": ["all", "windows", "chrome", "edge"], "description": "Fuente (default all)"},
            "query": {"type": "string", "description": "Filtro por target/url/usuario"},
            "reveal": {"type": "boolean", "description": "Si true intenta devolver password/secret"},
            "limit": {"type": "integer", "description": "Maximo de resultados por fuente (default 50)"}
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "clipboard_read",
        "description": "Lee el contenido actual del portapapeles de Windows.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
        "name": "clipboard_write",
        "description": "Escribe texto en el portapapeles de Windows.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string"},
        }, "required": ["text"]}
    }},
    {"type": "function", "function": {
        "name": "http_request",
        "description": "Realiza una petición HTTP completa (GET, POST, PUT, DELETE, PATCH). "
                       "Útil para APIs REST, webhooks, scraping con control total de headers y body.",
        "parameters": {"type": "object", "properties": {
            "url":     {"type": "string"},
            "method":  {"type": "string", "enum": ["GET","POST","PUT","DELETE","PATCH","HEAD"],
                        "description": "Método HTTP (default: GET)"},
            "headers": {"type": "object", "description": "Headers HTTP"},
            "body":    {"type": "string",  "description": "Body de la petición (JSON string u otro)"},
            "timeout": {"type": "integer", "description": "Timeout en segundos (default 30)"},
        }, "required": ["url"]}
    }},
    {"type": "function", "function": {
        "name": "search_files",
        "description": "Busca archivos en el sistema por nombre, extensión o contenido.",
        "parameters": {"type": "object", "properties": {
            "path":      {"type": "string",  "description": "Directorio raíz donde buscar"},
            "pattern":   {"type": "string",  "description": "Patrón glob (ej: *.py, *.log)"},
            "content":   {"type": "string",  "description": "Texto a buscar dentro de los archivos"},
            "recursive": {"type": "boolean", "description": "Buscar recursivamente (default: true)"},
            "max_results": {"type": "integer", "description": "Máximo de resultados (default: 50)"},
        }, "required": ["path"]}
    }},
    {"type": "function", "function": {
        "name": "kill_process",
        "description": "Termina un proceso por nombre o PID.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string",  "description": "Nombre del proceso (ej: chrome.exe)"},
            "pid":  {"type": "integer", "description": "PID del proceso"},
            "force": {"type": "boolean", "description": "Forzar terminación (default: true)"},
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "gpu_info",
        "description": "Obtiene información detallada de la GPU: uso, VRAM, temperatura, procesos en GPU.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
        "name": "open_browser",
        "description": "Abre una URL en el navegador predeterminado del sistema.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"},
        }, "required": ["url"]}
    }},
    {"type": "function", "function": {
        "name": "windows_notify",
        "description": "Envía una notificación toast de Windows al usuario.",
        "parameters": {"type": "object", "properties": {
            "title":   {"type": "string"},
            "message": {"type": "string"},
        }, "required": ["title", "message"]}
    }},
    {"type": "function", "function": {
        "name": "hash_file",
        "description": "Calcula el hash MD5/SHA256 de un archivo. Útil para verificar integridad.",
        "parameters": {"type": "object", "properties": {
            "path":      {"type": "string"},
            "algorithm": {"type": "string", "enum": ["md5","sha256","sha1","sha512"],
                          "description": "Algoritmo hash (default: sha256)"},
        }, "required": ["path"]}
    }},
    {"type": "function", "function": {
        "name": "diff_files",
        "description": "Compara dos archivos y muestra las diferencias línea a línea.",
        "parameters": {"type": "object", "properties": {
            "file_a": {"type": "string"},
            "file_b": {"type": "string"},
        }, "required": ["file_a", "file_b"]}
    }},
    {"type": "function", "function": {
        "name": "encode_decode",
        "description": "Codifica o decodifica texto: base64, URL encoding, hex, rot13.",
        "parameters": {"type": "object", "properties": {
            "text":      {"type": "string"},
            "operation": {"type": "string",
                          "enum": ["base64_encode","base64_decode","url_encode","url_decode",
                                   "hex_encode","hex_decode","rot13"]},
        }, "required": ["text", "operation"]}
    }},
    {"type": "function", "function": {
        "name": "network_info",
        "description": "Muestra interfaces de red, IPs, conexiones activas, tabla de rutas y DNS.",
        "parameters": {"type": "object", "properties": {
            "section": {"type": "string",
                        "enum": ["all","interfaces","connections","routes","dns"],
                        "description": "Sección (default: all)"},
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "env_vars",
        "description": "Lee o escribe variables de entorno del sistema.",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string", "enum": ["get","set","list","delete"]},
            "name":   {"type": "string", "description": "Nombre de la variable"},
            "value":  {"type": "string", "description": "Valor (solo para set)"},
            "scope":  {"type": "string", "enum": ["process","user","machine"],
                       "description": "Scope (default: process)"},
        }, "required": ["action"]}
    }},
    {"type": "function", "function": {
        "name": "memory_info",
        "description": "Información detallada de memoria RAM: total, disponible, uso por proceso.",
        "parameters": {"type": "object", "properties": {
            "top_n": {"type": "integer", "description": "Top N procesos por consumo (default: 10)"},
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Busca información actualizada en internet via DuckDuckGo. "
                       "Úsala para obtener noticias, documentación, CVEs, artículos técnicos recientes. "
                       "Devuelve títulos, snippets y URLs de los primeros resultados.",
        "parameters": {"type": "object", "properties": {
            "query":       {"type": "string",  "description": "Consulta de búsqueda"},
            "max_results": {"type": "integer", "description": "Número de resultados (default: 5, max: 10)"},
        }, "required": ["query"]}
    }},
    {"type": "function", "function": {
        "name": "rag_search",
        "description": "Busca en la base de conocimiento interna del agente (RAG). "
                       "Devuelve documentos relevantes previamente aprendidos.",
        "parameters": {"type": "object", "properties": {
            "query":   {"type": "string",  "description": "Consulta semántica"},
            "n_results": {"type": "integer", "description": "Número de resultados (default: 3)"},
        }, "required": ["query"]}
    }},
    {"type": "function", "function": {
        "name": "rag_add",
        "description": "Añade nueva información a la base de conocimiento interna del agente. "
                       "Úsala para guardar aprendizajes importantes, noticias técnicas, "
                       "soluciones a problemas o cualquier conocimiento que quieras recordar.",
        "parameters": {"type": "object", "properties": {
            "title":    {"type": "string", "description": "Título descriptivo del documento"},
            "content":  {"type": "string", "description": "Contenido a guardar"},
            "tags":     {"type": "array",  "items": {"type": "string"},
                         "description": "Etiquetas para clasificar (ej: ['security', 'python'])"},
            "platform": {"type": "string", "description": "Plataforma: windows, linux, macos, all (default: all)"},
        }, "required": ["title", "content"]}
    }},
    # ── Reverse engineering / binary analysis ─────────────────────────────
    {"type": "function", "function": {
        "name": "strings_extract",
        "description": "Extrae strings ASCII/Unicode imprimibles de un binario. "
                       "Esencial para análisis de malware, reverse engineering y extracción de IOCs.",
        "parameters": {"type": "object", "properties": {
            "path":       {"type": "string",  "description": "Ruta del binario"},
            "min_length": {"type": "integer", "description": "Longitud mínima de string (default: 4)"},
        }, "required": ["path"]}
    }},
    {"type": "function", "function": {
        "name": "hex_dump",
        "description": "Muestra volcado hexadecimal de un archivo o sección. "
                       "Útil para inspeccionar binarios, headers, shellcode.",
        "parameters": {"type": "object", "properties": {
            "path":   {"type": "string",  "description": "Ruta del archivo"},
            "offset": {"type": "integer", "description": "Offset en bytes donde empezar (default: 0)"},
            "length": {"type": "integer", "description": "Bytes a mostrar (default: 256, max: 4096)"},
        }, "required": ["path"]}
    }},
    {"type": "function", "function": {
        "name": "file_entropy",
        "description": "Calcula la entropía de Shannon de un archivo por secciones. "
                       "Entropía >7.2 indica packing/cifrado. Útil para detectar malware empaquetado.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Ruta del archivo"},
        }, "required": ["path"]}
    }},
    {"type": "function", "function": {
        "name": "pe_info",
        "description": "Analiza cabecera PE de ejecutables Windows (.exe, .dll, .sys). "
                       "Devuelve secciones, imports, exports, timestamp, arquitectura.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Ruta del ejecutable PE"},
        }, "required": ["path"]}
    }},
    {"type": "function", "function": {
        "name": "file_metadata",
        "description": "Metadatos completos de un archivo: tamaño, fechas, tipo detectado por magic bytes, "
                       "hashes MD5/SHA256, firma digital (Windows), versión del binario.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Ruta del archivo"},
        }, "required": ["path"]}
    }},
    # ── Advanced file exploration ──────────────────────────────────────────
    {"type": "function", "function": {
        "name": "grep_files",
        "description": "Busca patrones regex en archivos de un directorio con contexto de líneas. "
                       "Más potente que search_files: soporta regex, contexto, filtro por extensión.",
        "parameters": {"type": "object", "properties": {
            "directory":    {"type": "string",  "description": "Directorio raíz"},
            "pattern":      {"type": "string",  "description": "Expresión regular a buscar"},
            "file_glob":    {"type": "string",  "description": "Filtro de archivos ej: *.py (default: *)"},
            "recursive":    {"type": "boolean", "description": "Buscar recursivamente (default: true)"},
            "context_lines":{"type": "integer", "description": "Líneas de contexto antes/después (default: 2)"},
            "max_results":  {"type": "integer", "description": "Máximo resultados (default: 50)"},
        }, "required": ["directory", "pattern"]}
    }},
    # ── Windows system auditing ────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "registry_query",
        "description": "Lee claves o valores del registro de Windows. "
                       "Útil para auditoría de persistencia, configuración, malware analysis.",
        "parameters": {"type": "object", "properties": {
            "key":   {"type": "string", "description": "Clave de registro ej: HKEY_LOCAL_MACHINE\\SOFTWARE\\..."},
            "value": {"type": "string", "description": "Nombre del valor (opcional, si omites devuelve todos)"},
        }, "required": ["key"]}
    }},
    {"type": "function", "function": {
        "name": "list_services",
        "description": "Lista servicios de Windows con estado y tipo de inicio.",
        "parameters": {"type": "object", "properties": {
            "state":       {"type": "string", "enum": ["all", "running", "stopped"],
                            "description": "Filtrar por estado (default: all)"},
            "name_filter": {"type": "string", "description": "Filtrar por nombre (opcional)"},
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "check_persistence",
        "description": "Audita mecanismos de persistencia en Windows: registry autoruns, "
                       "carpetas de inicio, tareas programadas, servicios automáticos. "
                       "Esencial para análisis forense y detección de malware.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
        "name": "network_connections",
        "description": "Conexiones TCP activas con nombre del proceso propietario. "
                       "Más detallado que network_info: incluye qué proceso tiene cada socket.",
        "parameters": {"type": "object", "properties": {
            "state": {"type": "string", "enum": ["all", "listening", "established"],
                      "description": "Filtrar por estado (default: all)"},
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "process_tree",
        "description": "Árbol jerárquico de procesos (padre→hijo). "
                       "Útil para detectar procesos sospechosos inyectados o con parent incorrecto.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
        "name": "process_info",
        "description": "Información detallada de un proceso: línea de comandos, módulos cargados, "
                       "handles abiertos, variables de entorno, usuario.",
        "parameters": {"type": "object", "properties": {
            "pid":  {"type": "integer", "description": "PID del proceso"},
            "name": {"type": "string",  "description": "Nombre del proceso (alternativa al PID)"},
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "port_scan",
        "description": "Escanea puertos TCP en un host. Socket-based, no requiere nmap. "
                       "Útil para reconocimiento de red local, auditoría de servicios expuestos.",
        "parameters": {"type": "object", "properties": {
            "host":    {"type": "string",  "description": "IP o hostname (ej: 192.168.1.1, localhost)"},
            "ports":   {"type": "string",  "description": "Puertos: rango '1-1024', lista '80,443,8080' (default: 1-1024)"},
            "timeout": {"type": "number",  "description": "Timeout por puerto en segundos (default: 0.5)"},
        }, "required": ["host"]}
    }},
    # ── Web auditing ───────────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "ssl_info",
        "description": "Analiza certificado SSL/TLS de un host: versión TLS, cipher, "
                       "validez, emisor, SANs, expiración. Detecta certificados expirados o inválidos.",
        "parameters": {"type": "object", "properties": {
            "host": {"type": "string",  "description": "Hostname o IP"},
            "port": {"type": "integer", "description": "Puerto (default: 443)"},
        }, "required": ["host"]}
    }},
    {"type": "function", "function": {
        "name": "http_headers_check",
        "description": "Analiza cabeceras HTTP de seguridad: detecta si faltan HSTS, CSP, "
                       "X-Frame-Options, X-Content-Type-Options, CORS, etc. "
                       "Da score de seguridad y lista headers presentes/faltantes.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "description": "URL a analizar (ej: https://example.com)"},
        }, "required": ["url"]}
    }},
    {"type": "function", "function": {
        "name": "web_crawl",
        "description": "Rastrea una web y extrae todos los enlaces (internos y externos). "
                       "Útil para mapear la superficie de ataque, descubrir endpoints ocultos.",
        "parameters": {"type": "object", "properties": {
            "url":       {"type": "string",  "description": "URL inicial"},
            "depth":     {"type": "integer", "description": "Profundidad de rastreo (default: 1)"},
            "max_links": {"type": "integer", "description": "Máximo de links a recopilar (default: 50)"},
        }, "required": ["url"]}
    }},
    {"type": "function", "function": {
        "name": "dir_bruteforce",
        "description": "Enumeración de directorios y archivos web. Prueba paths comunes "
                       "(admin, login, .git, .env, api, backup...) con peticiones concurrentes. "
                       "No requiere herramientas externas.",
        "parameters": {"type": "object", "properties": {
            "url":         {"type": "string",  "description": "URL base (ej: http://target.com)"},
            "wordlist":    {"type": "string",
                            "description": "Lista de paths: 'common' (default, ~60 entries) o lista separada por comas"},
            "timeout":     {"type": "number",  "description": "Timeout por request en segundos (default: 5)"},
            "max_workers": {"type": "integer", "description": "Peticiones concurrentes (default: 20)"},
        }, "required": ["url"]}
    }},
    # ── Network auditing ───────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "dns_lookup",
        "description": "Consultas DNS: A, AAAA, MX, TXT, NS, CNAME, SOA, PTR. "
                       "Útil para reconocimiento de dominio, verificar SPF/DKIM, descubrir subdominios.",
        "parameters": {"type": "object", "properties": {
            "hostname":    {"type": "string", "description": "Dominio o IP"},
            "record_type": {"type": "string",
                            "enum": ["A","AAAA","MX","TXT","NS","CNAME","SOA","PTR","ANY"],
                            "description": "Tipo de registro DNS (default: A)"},
        }, "required": ["hostname"]}
    }},
    {"type": "function", "function": {
        "name": "whois_lookup",
        "description": "Consulta WHOIS de un dominio: registrar, fechas de creación/expiración, "
                       "name servers, estado. Útil para OSINT y reconocimiento.",
        "parameters": {"type": "object", "properties": {
            "domain": {"type": "string", "description": "Dominio (ej: example.com)"},
        }, "required": ["domain"]}
    }},
    {"type": "function", "function": {
        "name": "traceroute",
        "description": "Traza la ruta de red hasta un host mostrando cada salto (router). "
                       "Útil para diagnosticar pérdida de paquetes, latencia, rutas.",
        "parameters": {"type": "object", "properties": {
            "host":     {"type": "string",  "description": "IP o hostname de destino"},
            "max_hops": {"type": "integer", "description": "Máximo de saltos (default: 30)"},
        }, "required": ["host"]}
    }},
    {"type": "function", "function": {
        "name": "banner_grab",
        "description": "Captura el banner de un servicio TCP (HTTP, FTP, SMTP, SSH, Telnet...). "
                       "Revela versión del servidor, software, configuración.",
        "parameters": {"type": "object", "properties": {
            "host":    {"type": "string",  "description": "IP o hostname"},
            "port":    {"type": "integer", "description": "Puerto TCP"},
            "timeout": {"type": "number",  "description": "Timeout en segundos (default: 3)"},
        }, "required": ["host", "port"]}
    }},
    {"type": "function", "function": {
        "name": "ping_sweep",
        "description": "Descubre hosts activos en una subred. "
                       "Acepta CIDR (192.168.1.0/24) o rango (192.168.1.1-254). "
                       "Máximo 256 hosts por sweep.",
        "parameters": {"type": "object", "properties": {
            "network":    {"type": "string",  "description": "Red: CIDR '192.168.1.0/24' o rango '192.168.1.1-254'"},
            "timeout_ms": {"type": "integer", "description": "Timeout ICMP en ms (default: 500)"},
        }, "required": ["network"]}
    }},
    {"type": "function", "function": {
        "name": "arp_cache",
        "description": "Muestra la tabla ARP local: IPs y MACs de hosts en la red local. "
                       "Útil para descubrir dispositivos, detectar ARP poisoning.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    # ── Auto-conciencia y auto-modificación ───────────────────────────────────
    {"type": "function", "function": {
        "name": "list_self_files",
        "description": "Lista todos los archivos del proyecto CyberAgent (tu propio código fuente) "
                       "con rutas relativas, tamaños y fechas de modificación. "
                       "Úsala antes de editar tu propio código para orientarte.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
        "name": "syntax_check",
        "description": "Verifica la sintaxis de un archivo Python antes de aplicar cambios. "
                       "Compila el .py y devuelve 'ok: true' o el error exacto con número de línea. "
                       "Úsala siempre después de write_file() sobre tu propio código y ANTES de restart_self().",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string",
                     "description": "Ruta del archivo .py (absoluta o relativa al proyecto)"},
        }, "required": ["path"]}
    }},
    {"type": "function", "function": {
        "name": "restart_self",
        "description": "Reinicia CyberAgent limpiamente para aplicar los cambios en el código fuente. "
                       "Lanza una nueva instancia con 2 segundos de delay y cierra la actual. "
                       "SOLO usar después de verificar sintaxis con syntax_check(). "
                       "La conversación actual terminará; la nueva instancia arrancará fresca.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    # ── Watch mode (WATCH-001) ─────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "start_screenshot_watch",
        "description": "Activa el modo vigilancia: captura la pantalla del PC automáticamente cada N segundos "
                       "y envía cada captura al chat en tiempo real. Útil para supervisión remota desde iPhone, "
                       "monitoreo de procesos largos o seguimiento visual de tareas. "
                       "El servidor gestiona el bucle; el agente sigue libre para responder durante la vigilancia.",
        "parameters": {"type": "object", "properties": {
            "interval_sec": {"type": "integer",
                             "description": "Segundos entre capturas (mín 2, máx 60, default 5)"},
            "duration_sec":  {"type": "integer",
                             "description": "Duración total de la vigilancia en segundos (mín 5, máx 600, default 60)"},
            "monitor":       {"type": "integer",
                             "description": "Índice del monitor a capturar (0=principal, default 0)"},
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "stop_screenshot_watch",
        "description": "Detiene el modo vigilancia activo antes de que expire su duración. "
                       "Úsalo si ya tienes suficiente información o si el usuario pide parar.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
] + MOBILE_TOOLS_SCHEMA

DANGEROUS_TOOLS = {"shell", "write_file", "run_python", "install_package",
                   "uninstall_package", "kill_process", "env_vars"} | MOBILE_DANGEROUS

ACTIVE_SECURITY_TOOLS = {
    "port_scan", "dir_bruteforce", "ping_sweep", "banner_grab",
    "web_crawl", "http_headers_check", "ssl_info", "dns_lookup",
    "whois_lookup", "traceroute", "arp_cache", "network_connections",
}

SENSITIVE_ACCESS_TOOLS = {
    "credential_lookup", "clipboard_read", "clipboard_write", "click_screen",
    "type_text", "hotkey", "fill_form", "focus_window", "restart_self",
}

DANGEROUS_TOOLS |= ACTIVE_SECURITY_TOOLS | SENSITIVE_ACCESS_TOOLS

TOOL_CATEGORIES = {
    "core": {
        "shell", "read_file", "write_file", "list_directory", "run_python",
    },
    "web": {
        "web_search", "web_fetch", "http_request", "ssl_info",
        "http_headers_check", "dir_bruteforce", "web_crawl",
    },
    "files": {
        "search_files", "grep_files", "diff_files", "hash_file",
        "file_metadata",
    },
    "system": {
        "list_processes", "system_info", "memory_info", "gpu_info",
        "network_info", "env_vars", "process_tree", "process_info",
        "kill_process", "install_package", "uninstall_package",
    },
    "desktop": {
        "screenshot_pc", "list_monitors", "active_window", "list_windows",
        "focus_window", "click_screen", "type_text", "hotkey",
        "ocr_screen", "ui_tree", "fill_form", "credential_lookup",
        "clipboard_read", "clipboard_write", "open_browser",
        "windows_notify",
    },
    "network": {
        "port_scan", "dns_lookup", "whois_lookup", "traceroute",
        "banner_grab", "ping_sweep", "arp_cache", "network_connections",
    },
    "forensics": {
        "strings_extract", "hex_dump", "file_entropy", "pe_info",
        "file_metadata", "registry_query", "list_services",
        "check_persistence",
    },
    "encode": {"encode_decode"},
    "rag": {"rag_search", "rag_add"},
    "self": {"list_self_files", "syntax_check", "restart_self"},
}

TOOL_USE_GUIDES = {
    "web": "Audita URLs y APIs. Usa solo sobre activos propios o autorizados.",
    "network": "Descubre red, puertos y servicios. Requiere autorizacion sobre el objetivo.",
    "forensics": "Inspecciona archivos, binarios, servicios y persistencia local.",
    "desktop": "Opera el PC local con inspeccion visual y acciones de usuario.",
    "system": "Lee o modifica estado del sistema local segun permisos.",
    "files": "Busca, compara y verifica archivos locales.",
    "core": "Ejecucion basica y lectura/escritura local.",
    "encode": "Transforma datos para analisis tecnico.",
    "rag": "Consulta o amplia la base de conocimiento local.",
    "self": "Inspecciona o reinicia el propio agente.",
}

_TOOL_SCHEMA_INDEX = {t["function"]["name"]: t for t in TOOLS_SCHEMA}
_TOOL_TO_CATEGORY = {
    name: category
    for category, names in TOOL_CATEGORIES.items()
    for name in names
}


def _tool_description(name: str) -> str:
    schema = _TOOL_SCHEMA_INDEX.get(name, {})
    return schema.get("function", {}).get("description", "")


def get_tool_meta(name: str) -> dict:
    category = _TOOL_TO_CATEGORY.get(name)
    if category is None and name.startswith(("mobile_", "ios_")):
        category = "mobile"
    category = category or "other"
    dangerous = name in DANGEROUS_TOOLS
    return {
        "name": name,
        "category": category,
        "risk": "high" if dangerous else "low",
        "default_permission": "ask" if dangerous else "auto",
        "dangerous": dangerous,
        "guide": TOOL_USE_GUIDES.get(category, "Herramienta disponible en el agente."),
        "description": _tool_description(name),
    }


def get_tool_catalog() -> list[dict]:
    return [get_tool_meta(t["function"]["name"]) for t in TOOLS_SCHEMA]


def tool_names_by_category(category: str) -> set[str]:
    if category == "mobile":
        return {t["function"]["name"] for t in MOBILE_TOOLS_SCHEMA}
    return set(TOOL_CATEGORIES.get(category, set()))


def tool_event_payload(tool_id: str, name: str, args: dict) -> dict:
    meta = get_tool_meta(name)
    return {
        "id": tool_id,
        "name": name,
        "args": args,
        "dangerous": meta["dangerous"],
        "category": meta["category"],
        "risk": meta["risk"],
        "permission": meta["default_permission"],
        "guide": meta["guide"],
    }


def is_dangerous(name: str) -> bool:
    return name in DANGEROUS_TOOLS


def execute_tool(name: str, args: dict) -> dict:
    try:
        dispatch = {
            "shell":             lambda: _shell(
                                     args.get("command", ""),
                                     args.get("shell_type", "powershell"),
                                     int(args.get("timeout", 60)),
                                 ),
            "read_file":         lambda: _read_file(
                                     args["path"],
                                     args.get("offset", 0),
                                     args.get("limit"),
                                 ),
            "write_file":        lambda: _write_file(
                                     args["path"],
                                     args["content"],
                                     bool(args.get("append", False)),
                                 ),
            "list_directory":    lambda: _list_dir(
                                     args["path"],
                                     bool(args.get("recursive", False)),
                                 ),
            "web_fetch":         lambda: _web_fetch(
                                     args["url"],
                                     args.get("headers", {}),
                                 ),
            "run_python":        lambda: _run_python(
                                     args["code"],
                                     int(args.get("timeout", 30)),
                                 ),
            "list_processes":    lambda: _list_processes(
                                     args.get("filter_name", ""),
                                     args.get("sort_by", "memory"),
                                 ),
            "install_package":   lambda: _install_package(
                                     args["package"],
                                     args["manager"],
                                     args.get("version", ""),
                                 ),
            "uninstall_package": lambda: _uninstall_package(
                                     args["package"],
                                     args["manager"],
                                 ),
            "system_info":       lambda: _system_info(
                                     args.get("section", "all"),
                                 ),
        }
        superagent = {
            "screenshot_pc":   lambda: _screenshot_pc(int(args.get("monitor", 0))),
            "list_monitors":   lambda: _list_monitors(),
            "active_window":   lambda: _active_window(),
            "list_windows":    lambda: _list_windows(
                                   args.get("title_filter", ""),
                                   args.get("process_filter", ""),
                                   int(args.get("limit", 80))),
            "focus_window":    lambda: _focus_window(
                                   args.get("hwnd"), args.get("title", ""),
                                   args.get("pid")),
            "click_screen":    lambda: _click_screen(
                                   int(args["x"]), int(args["y"]),
                                   args.get("button", "left"),
                                   int(args.get("clicks", 1))),
            "type_text":       lambda: _type_text(
                                   args["text"], int(args.get("interval_ms", 0))),
            "hotkey":          lambda: _hotkey(args["keys"]),
            "ocr_screen":      lambda: _ocr_screen(
                                   int(args.get("monitor", 0)),
                                   args.get("x"), args.get("y"),
                                   args.get("width"), args.get("height")),
            "ui_tree":         lambda: _ui_tree(
                                   args.get("hwnd"), int(args.get("depth", 2)),
                                   int(args.get("limit", 120))),
            "fill_form":       lambda: _fill_form(
                                   args.get("actions", []), args.get("hwnd"),
                                   args.get("title", "")),
            "credential_lookup": lambda: _credential_lookup(
                                   args.get("source", "all"),
                                   args.get("query", ""),
                                   bool(args.get("reveal", False)),
                                   int(args.get("limit", 50))),            "clipboard_read":  lambda: _clipboard_read(),
            "clipboard_write": lambda: _clipboard_write(args["text"]),
            "http_request":    lambda: _http_request(
                                   args["url"], args.get("method","GET"),
                                   args.get("headers",{}), args.get("body",""),
                                   int(args.get("timeout",30))),
            "search_files":    lambda: _search_files(
                                   args["path"], args.get("pattern","*"),
                                   args.get("content",""),
                                   bool(args.get("recursive",True)),
                                   int(args.get("max_results",50))),
            "kill_process":    lambda: _kill_process(
                                   args.get("name",""), args.get("pid"),
                                   bool(args.get("force",True))),
            "gpu_info":        lambda: _gpu_info(),
            "open_browser":    lambda: _open_browser(args["url"]),
            "windows_notify":  lambda: _windows_notify(args["title"], args["message"]),
            "hash_file":       lambda: _hash_file(args["path"], args.get("algorithm","sha256")),
            "diff_files":      lambda: _diff_files(args["file_a"], args["file_b"]),
            "encode_decode":   lambda: _encode_decode(args["text"], args["operation"]),
            "network_info":    lambda: _network_info(args.get("section","all")),
            "env_vars":        lambda: _env_vars(
                                   args["action"], args.get("name",""),
                                   args.get("value",""), args.get("scope","process")),
            "memory_info":     lambda: _memory_info(int(args.get("top_n",10))),
            "web_search":      lambda: _web_search(
                                   args["query"], int(args.get("max_results", 5))),
            "rag_search":      lambda: _rag_search(
                                   args["query"], int(args.get("n_results", 3))),
            "rag_add":         lambda: _rag_add(
                                   args["title"], args["content"],
                                   args.get("tags", []), args.get("platform", "all")),
            # RE / binary analysis
            "strings_extract": lambda: _strings_extract(
                                   args["path"], int(args.get("min_length", 4))),
            "hex_dump":        lambda: _hex_dump(
                                   args["path"], int(args.get("offset", 0)),
                                   int(args.get("length", 256))),
            "file_entropy":    lambda: _file_entropy(args["path"]),
            "pe_info":         lambda: _pe_info(args["path"]),
            "file_metadata":   lambda: _file_metadata(args["path"]),
            # Advanced file search
            "grep_files":      lambda: _grep_files(
                                   args["directory"], args["pattern"],
                                   args.get("file_glob", "*"),
                                   bool(args.get("recursive", True)),
                                   int(args.get("context_lines", 2)),
                                   int(args.get("max_results", 50))),
            # Security auditing
            "registry_query":       lambda: _registry_query(
                                        args["key"], args.get("value", "")),
            "list_services":        lambda: _list_services(
                                        args.get("state", "all"),
                                        args.get("name_filter", "")),
            "check_persistence":    lambda: _check_persistence(),
            "network_connections":  lambda: _network_connections(
                                        args.get("state", "all")),
            "process_tree":         lambda: _process_tree(),
            "process_info":         lambda: _process_info(
                                        args.get("pid"), args.get("name", "")),
            "port_scan":            lambda: _port_scan(
                                        args["host"],
                                        args.get("ports", "1-1024"),
                                        float(args.get("timeout", 0.5))),
            # Web auditing
            "ssl_info":             lambda: _ssl_info(
                                        args["host"], int(args.get("port", 443))),
            "http_headers_check":   lambda: _http_headers_check(args["url"]),
            "web_crawl":            lambda: _web_crawl(
                                        args["url"],
                                        int(args.get("depth", 1)),
                                        int(args.get("max_links", 50))),
            "dir_bruteforce":       lambda: _dir_bruteforce(
                                        args["url"],
                                        args.get("wordlist", "common"),
                                        float(args.get("timeout", 5.0)),
                                        int(args.get("max_workers", 20))),
            # Network auditing
            "dns_lookup":           lambda: _dns_lookup(
                                        args["hostname"],
                                        args.get("record_type", "A")),
            "whois_lookup":         lambda: _whois_lookup(args["domain"]),
            "traceroute":           lambda: _traceroute(
                                        args["host"], int(args.get("max_hops", 30))),
            "banner_grab":          lambda: _banner_grab(
                                        args["host"], int(args["port"]),
                                        float(args.get("timeout", 3.0))),
            "ping_sweep":           lambda: _ping_sweep(
                                        args["network"], int(args.get("timeout_ms", 500))),
            "arp_cache":            lambda: _arp_cache(),
            # Auto-conciencia
            "list_self_files":      lambda: _sa_module().list_self_files(),
            "syntax_check":         lambda: _sa_module().syntax_check(args["path"]),
            "restart_self":         lambda: _sa_module().restart_self(),
            # Watch mode (WATCH-001) — returns config; server drives the loop
            "start_screenshot_watch": lambda: {
                "watch_started": True,
                "interval_sec":  max(2, min(60,  int(args.get("interval_sec",  5)))),
                "duration_sec":  max(5, min(600, int(args.get("duration_sec",  60)))),
                "monitor":       int(args.get("monitor", 0)),
                "message": (
                    f"Modo vigilancia activado: captura cada "
                    f"{max(2, min(60, int(args.get('interval_sec', 5))))}s "
                    f"durante {max(5, min(600, int(args.get('duration_sec', 60))))}s"
                ),
            },
            "stop_screenshot_watch": lambda: {"watch_stopped": True},
        }
        all_tools = {**dispatch, **superagent}
        if name in all_tools:
            if name in _CACHEABLE_TOOLS:
                key = _cache_key(name, args)
                cached = _cache_get(key)
                if cached is not None:
                    return {**cached, "_cached": True}
                result = all_tools[name]()
                if "error" not in result:
                    _cache_set(key, result)
                return result
            return all_tools[name]()
        return execute_mobile_tool(name, args)
    except KeyError as e:
        return {"error": f"Argumento requerido: {e}"}
    except Exception as e:
        return {"error": str(e)}


# ── Implementaciones ───────────────────────────────────────────────────────

_VENV_SCRIPTS = os.path.dirname(sys.executable).replace("\\", "/")
_PATH_REFRESH = (
    "$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine')"
    " + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')"
    f" + ';{_VENV_SCRIPTS}'; "
    f"Set-Alias python '{sys.executable}'; "
    f"Set-Alias python3 '{sys.executable}'; "
)

def _shell(command: str, shell_type: str = "powershell", timeout: int = 60) -> dict:
    if shell_type == "bash":
        cmd = ["wsl", "-d", "Ubuntu-24.04", "--", "bash", "-c", command]
    elif shell_type == "cmd":
        cmd = ["cmd.exe", "/c", command]
    else:
        # Refresca PATH desde el registro en cada comando para ver herramientas
        # recién instaladas (winget actualiza el registro, no el proceso actual)
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
               _PATH_REFRESH + command]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
        return {
            "stdout":     r.stdout[:10000],
            "stderr":     r.stderr[:3000],
            "returncode": r.returncode,
            "shell":      shell_type,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Timeout ({timeout}s)"}


def _read_file(path: str, offset: int = 0, limit=None) -> dict:
    path = os.path.expandvars(os.path.expanduser(path))
    if not os.path.exists(path):
        return {"error": f"No encontrado: {path}"}
    if os.path.isdir(path):
        return {"error": f"Es un directorio: {path}"}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    total = len(lines)
    if offset:
        lines = lines[offset:]
    if limit:
        lines = lines[:limit]
    content = "".join(lines)
    return {
        "path":    path,
        "content": content[:20000],
        "size":    os.path.getsize(path),
        "lines":   total,
        "shown":   f"{offset}–{offset + len(lines)}",
    }


def _write_file(path: str, content: str, append: bool = False) -> dict:
    path = os.path.expandvars(os.path.expanduser(path))
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as f:
        f.write(content)
    return {"success": True, "path": path, "bytes": len(content.encode()), "mode": mode}


def _list_dir(path: str, recursive: bool = False) -> dict:
    path = os.path.expandvars(os.path.expanduser(path))
    if not os.path.exists(path):
        return {"error": f"No encontrado: {path}"}
    entries = []
    if recursive:
        for root, dirs, files in os.walk(path):
            for d in dirs:
                full = os.path.join(root, d)
                entries.append({"name": os.path.relpath(full, path), "type": "dir", "size": None})
            for f in files:
                full = os.path.join(root, f)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    size = None
                entries.append({"name": os.path.relpath(full, path), "type": "file", "size": size})
            if len(entries) > 500:
                entries.append({"truncated": True})
                break
    else:
        for e in os.scandir(path):
            entries.append({
                "name":     e.name,
                "type":     "dir" if e.is_dir() else "file",
                "size":     e.stat().st_size if e.is_file() else None,
                "modified": datetime.fromtimestamp(e.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    return {"path": path, "entries": sorted(entries, key=lambda x: (x.get("type", ""), x.get("name", "")))}


def _is_safe_external_url(url: str) -> tuple[bool, str]:
    """Block requests to loopback, link-local and private RFC-1918 ranges."""
    import ipaddress
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, f"scheme '{parsed.scheme}' not allowed"
        host = parsed.hostname or ""
        # Block by hostname
        if host in ("localhost", ""):
            return False, "loopback hostname blocked"
        try:
            addr = ipaddress.ip_address(host)
            if addr.is_loopback or addr.is_private or addr.is_link_local or addr.is_reserved:
                return False, f"private/reserved IP {host} blocked"
        except ValueError:
            pass  # hostname, not IP — allow it
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _web_fetch(url: str, headers: dict | None = None) -> dict:
    import urllib.request, re
    safe, reason = _is_safe_external_url(url)
    if not safe:
        return {"error": f"URL bloqueada por política de seguridad: {reason}"}
    default_headers = {"User-Agent": "Mozilla/5.0 (CyberAgent/1.0)"}
    if headers:
        default_headers.update(headers)
    req = urllib.request.Request(url, headers=default_headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return {"error": str(e)}
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return {"url": url, "content": text[:15000], "length": len(text)}


def _run_python(code: str, timeout: int = 30) -> dict:
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp = f.name
    try:
        r = subprocess.run(
            [sys.executable, tmp],
            capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
        return {
            "stdout":     r.stdout[:10000],
            "stderr":     r.stderr[:3000],
            "returncode": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Timeout ({timeout}s)"}
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _list_processes(filter_name: str = "", sort_by: str = "memory") -> dict:
    import psutil
    sort_keys = {
        "memory": lambda p: (p.get("mem_mb", 0), 0),
        "cpu":    lambda p: (p.get("cpu", 0), 0),
        "name":   lambda p: (p.get("name", ""), 0),
        "pid":    lambda p: (p.get("pid", 0), 0),
    }
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
        try:
            info = p.info
            if filter_name and filter_name.lower() not in info["name"].lower():
                continue
            procs.append({
                "pid":    info["pid"],
                "name":   info["name"],
                "mem_mb": round(info["memory_info"].rss / 1024 ** 2, 1),
                "cpu":    info["cpu_percent"],
                "status": info["status"],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    key = sort_keys.get(sort_by, sort_keys["memory"])
    procs.sort(key=key, reverse=sort_by in ("memory", "cpu"))
    return {"processes": procs[:60], "total": len(procs)}


def _install_package(package: str, manager: str, version: str = "") -> dict:
    pkg = f"{package}=={version}" if version and manager == "pip" else package
    if version and manager in ("choco", "winget"):
        pkg = f"{package} --version {version}"

    cmds = {
        "pip":    [sys.executable, "-m", "pip", "install", "--upgrade", pkg],
        "winget": ["winget", "install", package] + (["--version", version] if version else []) + [
                   "--accept-package-agreements", "--accept-source-agreements",
                   "--silent", "--disable-interactivity"],
        "npm":    ["npm", "install", "-g", pkg],
        "choco":  ["choco", "install", pkg, "-y"],
        "apt":    ["wsl", "-d", "Ubuntu-24.04", "--", "bash", "-c",
                   f"sudo apt-get update && sudo apt-get install -y {package}"],
    }
    if manager not in cmds:
        return {"error": f"Gestor no soportado: {manager}"}

    try:
        r = subprocess.run(
            cmds[manager], capture_output=True, text=True,
            timeout=300, encoding="utf-8", errors="replace",
        )
        return {
            "manager":    manager,
            "package":    package,
            "stdout":     r.stdout[:6000],
            "stderr":     r.stderr[:2000],
            "returncode": r.returncode,
            "success":    r.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Timeout (300s) — la instalación tardó demasiado"}
    except FileNotFoundError:
        return {"error": f"'{manager}' no está instalado o no está en el PATH"}


def _uninstall_package(package: str, manager: str) -> dict:
    cmds = {
        "pip":    [sys.executable, "-m", "pip", "uninstall", "-y", package],
        "winget": ["winget", "uninstall", package, "--silent", "--disable-interactivity"],
        "npm":    ["npm", "uninstall", "-g", package],
        "choco":  ["choco", "uninstall", package, "-y"],
        "apt":    ["wsl", "-d", "Ubuntu-24.04", "--", "bash", "-c",
                   f"sudo apt-get remove -y {package}"],
    }
    if manager not in cmds:
        return {"error": f"Gestor no soportado: {manager}"}
    try:
        r = subprocess.run(
            cmds[manager], capture_output=True, text=True,
            timeout=120, encoding="utf-8", errors="replace",
        )
        return {
            "manager":    manager,
            "package":    package,
            "stdout":     r.stdout[:4000],
            "returncode": r.returncode,
            "success":    r.returncode == 0,
        }
    except FileNotFoundError:
        return {"error": f"'{manager}' no encontrado"}


def _system_info(section: str = "all") -> dict:
    import platform
    result = {}

    if section in ("all", "os"):
        result["os"] = {
            "system":   platform.system(),
            "version":  platform.version(),
            "release":  platform.release(),
            "machine":  platform.machine(),
            "hostname": platform.node(),
            "python":   platform.python_version(),
        }

    if section in ("all", "hardware"):
        try:
            import psutil
            vm = psutil.virtual_memory()
            disk = psutil.disk_usage(os.path.abspath(os.sep))
            result["hardware"] = {
                "cpu_cores":    psutil.cpu_count(),
                "cpu_percent":  psutil.cpu_percent(interval=1),
                "ram_total_gb": round(vm.total / 1024 ** 3, 1),
                "ram_used_pct": vm.percent,
                "disk_total_gb": round(disk.total / 1024 ** 3, 1),
                "disk_free_gb":  round(disk.free / 1024 ** 3, 1),
            }
        except ImportError:
            result["hardware"] = {"error": "psutil no disponible"}

    if section in ("all", "network"):
        try:
            import socket, psutil
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            connections = [
                {"laddr": f"{c.laddr.ip}:{c.laddr.port}", "status": c.status}
                for c in psutil.net_connections()
                if c.status in ("LISTEN", "ESTABLISHED") and c.laddr
            ][:20]
            result["network"] = {
                "hostname":    hostname,
                "local_ip":    local_ip,
                "connections": connections,
            }
        except Exception as e:
            result["network"] = {"error": str(e)}

    if section in ("all", "processes"):
        result["processes"] = _list_processes(sort_by="memory")

    if section in ("all", "tools"):
        tools_check = ["git", "python", "pip", "node", "npm", "docker",
                       "nmap", "curl", "wget", "wsl", "winget", "choco"]
        result["tools"] = {t: shutil.which(t) is not None for t in tools_check}

    return result


# ── Superagent tool implementations ───────────────────────────────────────────

def _screenshot_pc(monitor: int = 0) -> dict:
    try:
        import mss, base64, io
        from PIL import Image
        with mss.mss() as sct:
            monitors = sct.monitors
            idx = min(monitor + 1, len(monitors) - 1)
            shot = sct.grab(monitors[idx])
            img  = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            buf  = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            b64  = base64.b64encode(buf.getvalue()).decode()
        return {"screenshot_base64": b64, "format": "jpeg",
                "size": f"{shot.width}x{shot.height}", "monitor": idx}
    except ImportError:
        # Fallback: PowerShell
        _tmp = os.environ.get("TEMP", os.environ.get("TMP", "C:\\Windows\\Temp"))
        _ss_path = os.path.join(_tmp, "ca_ss.png")
        r = _shell(
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$s=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
            "$b=New-Object System.Drawing.Bitmap($s.Width,$s.Height); "
            "$g=[System.Drawing.Graphics]::FromImage($b); "
            "$g.CopyFromScreen($s.Location,[System.Drawing.Point]::Empty,$s.Size); "
            f'$b.Save("{_ss_path.replace(chr(39), chr(39)+chr(39))}"); echo "ok"', "powershell")
        if r.get("returncode") == 0:
            import base64
            with open(_ss_path, "rb") as _fh:
                data = _fh.read()
            return {"screenshot_base64": base64.b64encode(data).decode(), "format": "png"}
        return {"error": "Instala mss: pip install mss"}
    except Exception as e:
        return {"error": str(e)}

def _win_ctypes():
    import ctypes
    from ctypes import wintypes
    return ctypes, wintypes, ctypes.windll.user32, ctypes.windll.kernel32

def _rect_to_dict(rect) -> dict:
    return {
        "left": int(rect.left), "top": int(rect.top),
        "right": int(rect.right), "bottom": int(rect.bottom),
        "width": int(rect.right - rect.left),
        "height": int(rect.bottom - rect.top),
    }

def _window_info(hwnd: int) -> dict | None:
    import psutil
    ctypes, wintypes, user32, _kernel32 = _win_ctypes()
    if not hwnd or not user32.IsWindow(hwnd):
        return None
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    process = ""
    try:
        process = psutil.Process(pid.value).name()
    except Exception:
        pass
    return {
        "hwnd": int(hwnd),
        "title": buf.value,
        "pid": int(pid.value),
        "process": process,
        "rect": _rect_to_dict(rect),
        "visible": bool(user32.IsWindowVisible(hwnd)),
        "minimized": bool(user32.IsIconic(hwnd)),
    }

def _list_monitors() -> dict:
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32

        class MONITORINFOEXW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
                ("szDevice", wintypes.WCHAR * 32),
            ]

        monitors = []
        enum_proc_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
            ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
        )

        def _callback(hmonitor, _hdc, _lprc, _data):
            info = MONITORINFOEXW()
            info.cbSize = ctypes.sizeof(MONITORINFOEXW)
            user32.GetMonitorInfoW(hmonitor, ctypes.byref(info))
            scale = None
            try:
                shcore = ctypes.windll.shcore
                dpi_x = ctypes.c_uint()
                dpi_y = ctypes.c_uint()
                if shcore.GetDpiForMonitor(hmonitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)) == 0:
                    scale = round(dpi_x.value / 96, 2)
            except Exception:
                pass
            monitors.append({
                "index": len(monitors),
                "device": info.szDevice,
                "primary": bool(info.dwFlags & 1),
                "monitor": _rect_to_dict(info.rcMonitor),
                "work_area": _rect_to_dict(info.rcWork),
                "scale": scale,
            })
            return True

        user32.EnumDisplayMonitors(0, 0, enum_proc_type(_callback), 0)
        return {"monitors": monitors, "count": len(monitors)}
    except Exception as e:
        return {"error": str(e)}

def _active_window() -> dict:
    try:
        _ctypes, _wintypes, user32, _kernel32 = _win_ctypes()
        return _window_info(user32.GetForegroundWindow()) or {"error": "No active window"}
    except Exception as e:
        return {"error": str(e)}

def _list_windows(title_filter: str = "", process_filter: str = "", limit: int = 80) -> dict:
    try:
        import ctypes
        from ctypes import wintypes
        _ctypes, _wintypes, user32, _kernel32 = _win_ctypes()
        title_filter = (title_filter or "").lower()
        process_filter = (process_filter or "").lower()
        windows = []
        enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def _callback(hwnd, _data):
            if len(windows) >= max(1, limit):
                return False
            if not user32.IsWindowVisible(hwnd):
                return True
            info = _window_info(hwnd)
            if not info or not info.get("title"):
                return True
            if title_filter and title_filter not in info["title"].lower():
                return True
            if process_filter and process_filter not in info.get("process", "").lower():
                return True
            windows.append(info)
            return True

        user32.EnumWindows(enum_proc_type(_callback), 0)
        return {"windows": windows, "count": len(windows)}
    except Exception as e:
        return {"error": str(e)}

def _resolve_window(hwnd=None, title: str = "", pid=None) -> int | None:
    if hwnd:
        return int(hwnd)
    windows = _list_windows(title_filter=title or "", limit=200).get("windows", [])
    if pid:
        windows = [w for w in windows if int(w.get("pid") or 0) == int(pid)]
    if title:
        title_l = title.lower()
        exact = [w for w in windows if w.get("title", "").lower() == title_l]
        if exact:
            return int(exact[0]["hwnd"])
    return int(windows[0]["hwnd"]) if windows else None

def _focus_window(hwnd=None, title: str = "", pid=None) -> dict:
    try:
        _ctypes, _wintypes, user32, _kernel32 = _win_ctypes()
        target = _resolve_window(hwnd, title, pid)
        if not target:
            return {"ok": False, "error": "Ventana no encontrada"}
        user32.ShowWindow(target, 9 if user32.IsIconic(target) else 5)
        ok = bool(user32.SetForegroundWindow(target))
        return {"ok": ok, "window": _window_info(target)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _click_screen(x: int, y: int, button: str = "left", clicks: int = 1) -> dict:
    try:
        import ctypes, time
        user32 = ctypes.windll.user32
        events = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010), "middle": (0x0020, 0x0040)}
        down, up = events.get((button or "left").lower(), events["left"])
        user32.SetCursorPos(int(x), int(y))
        for _ in range(max(1, int(clicks))):
            user32.mouse_event(down, 0, 0, 0, 0)
            user32.mouse_event(up, 0, 0, 0, 0)
            time.sleep(0.05)
        return {"ok": True, "x": x, "y": y, "button": button, "clicks": clicks}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _type_text(text: str, interval_ms: int = 0) -> dict:
    try:
        import ctypes, time
        user32 = ctypes.windll.user32
        for ch in text:
            code = ord(ch)
            user32.keybd_event(0, code, 0x0004, 0)
            user32.keybd_event(0, code, 0x0004 | 0x0002, 0)
            if interval_ms:
                time.sleep(max(0, interval_ms) / 1000)
        return {"ok": True, "chars": len(text)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _hotkey(keys: list) -> dict:
    try:
        import ctypes, time
        user32 = ctypes.windll.user32
        keymap = {
            "ctrl": 0x11, "control": 0x11, "shift": 0x10, "alt": 0x12,
            "win": 0x5B, "cmd": 0x5B, "enter": 0x0D, "return": 0x0D,
            "tab": 0x09, "esc": 0x1B, "escape": 0x1B, "space": 0x20,
            "backspace": 0x08, "delete": 0x2E, "home": 0x24, "end": 0x23,
            "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
            "f11": 0x7A,
        }
        vk_codes = []
        for key in keys:
            k = str(key).lower()
            vk = ord(k.upper()) if len(k) == 1 else keymap.get(k)
            if not vk:
                return {"ok": False, "error": f"Tecla no soportada: {key}"}
            vk_codes.append(vk)
        for vk in vk_codes:
            user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.02)
        for vk in reversed(vk_codes):
            user32.keybd_event(vk, 0, 0x0002, 0)
            time.sleep(0.02)
        return {"ok": True, "keys": keys}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _ocr_screen(monitor: int = 0, x=None, y=None, width=None, height=None) -> dict:
    try:
        import tempfile
        from PIL import Image
        try:
            import mss
        except ImportError:
            return {"error": "Falta mss. Instala con: pip install mss pillow pytesseract"}
        with mss.mss() as sct:
            mons = sct.monitors
            idx = min(max(0, monitor) + 1, len(mons) - 1)
            region = dict(mons[idx])
            if all(v is not None for v in (x, y, width, height)):
                region = {"left": int(x), "top": int(y), "width": int(width), "height": int(height)}
            shot = sct.grab(region)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        path = os.path.join(tempfile.gettempdir(), "cyberagent_ocr_screen.png")
        img.save(path)
        try:
            import pytesseract
            tesseract_cmd = (
                shutil.which("tesseract")
                or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                or r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
            )
            if tesseract_cmd and os.path.exists(tesseract_cmd):
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            text = pytesseract.image_to_string(img)
            return {
                "ok": True,
                "text": text[:12000],
                "image_path": path,
                "region": region,
                "tesseract_cmd": getattr(pytesseract.pytesseract, "tesseract_cmd", None),
            }
        except Exception as e:
            return {"ok": False, "image_path": path, "region": region, "error": f"OCR no disponible: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _ui_tree(hwnd=None, depth: int = 2, limit: int = 120) -> dict:
    active = _active_window()
    target = int(hwnd) if hwnd else active.get("hwnd")
    if not target:
        return {"error": "No hay ventana objetivo"}
    script = rf"""
$hwnd = [IntPtr]{target}
$maxDepth = {max(0, depth)}
$limit = {max(1, limit)}
Add-Type -AssemblyName UIAutomationClient
$root = [System.Windows.Automation.AutomationElement]::FromHandle($hwnd)
$out = New-Object System.Collections.ArrayList
function Walk($el, $depth) {{
  if ($null -eq $el -or $out.Count -ge $limit) {{ return }}
  $r = $el.Current.BoundingRectangle
  [void]$out.Add([pscustomobject]@{{
    depth=$depth; name=$el.Current.Name; automation_id=$el.Current.AutomationId;
    class_name=$el.Current.ClassName; control_type=$el.Current.ControlType.ProgrammaticName;
    enabled=$el.Current.IsEnabled; rect=@{{left=$r.Left; top=$r.Top; width=$r.Width; height=$r.Height}}
  }})
  if ($depth -ge $maxDepth) {{ return }}
  $children = $el.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
  foreach ($c in $children) {{ Walk $c ($depth + 1) }}
}}
Walk $root 0
$out | ConvertTo-Json -Depth 6
"""
    r = _shell(script, "powershell", timeout=20)
    if r.get("returncode") != 0:
        return {"error": r.get("stderr") or r.get("stdout")}
    try:
        nodes = json.loads(r.get("stdout") or "[]")
        if isinstance(nodes, dict):
            nodes = [nodes]
        return {"hwnd": target, "nodes": nodes, "count": len(nodes)}
    except Exception:
        return {"hwnd": target, "raw": r.get("stdout", "")[:12000]}

def _fill_form(actions: list, hwnd=None, title: str = "") -> dict:
    import time
    events = []
    if hwnd or title:
        events.append({"focus": _focus_window(hwnd=hwnd, title=title)})
        time.sleep(0.25)
    for action in actions:
        kind = (action.get("action") or action.get("type") or "").lower()
        if kind == "click":
            events.append({"click": _click_screen(int(action["x"]), int(action["y"]), action.get("button", "left"), int(action.get("clicks", 1)))})
        elif kind == "type":
            events.append({"type": _type_text(str(action.get("text", "")), int(action.get("interval_ms", 0)))})
        elif kind == "hotkey":
            events.append({"hotkey": _hotkey(action.get("keys", []))})
        elif kind == "wait":
            ms = int(action.get("ms", 500))
            time.sleep(max(0, ms) / 1000)
            events.append({"wait": ms})
        else:
            events.append({"error": f"Accion no soportada: {kind}", "action": action})
        time.sleep(float(action.get("after_ms", 80)) / 1000)
    return {"ok": True, "events": events}

def _credential_lookup(source: str = "all", query: str = "", reveal: bool = False, limit: int = 50) -> dict:
    source = (source or "all").lower()
    query_l = (query or "").lower()
    results = []
    errors = []
    if source in ("all", "windows"):
        r = _shell("cmdkey /list", "cmd", timeout=10)
        text = r.get("stdout", "")
        entries = []
        current = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                if current:
                    entries.append(current); current = {}
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                current[k.strip().lower().replace(" ", "_")] = v.strip()
        if current:
            entries.append(current)
        for e in entries:
            blob = json.dumps(e, ensure_ascii=False).lower()
            if query_l and query_l not in blob:
                continue
            e["source"] = "windows"
            e["secret"] = None
            e["note"] = "Windows cmdkey lista metadatos; no expone passwords en claro."
            results.append(e)
            if len(results) >= limit:
                break
    if source in ("all", "chrome", "edge") and len(results) < limit:
        try:
            results.extend(_chromium_credentials(source, query_l, reveal, max(1, limit - len(results))))
        except Exception as e:
            errors.append(str(e))
    return {"results": results[:limit], "count": min(len(results), limit), "reveal": reveal, "errors": errors}

def _chromium_credentials(source: str, query_l: str, reveal: bool, limit: int) -> list:
    import sqlite3, tempfile
    bases = []
    local = os.environ.get("LOCALAPPDATA", "")
    if source in ("all", "chrome"):
        bases.append(("chrome", os.path.join(local, "Google", "Chrome", "User Data")))
    if source in ("all", "edge"):
        bases.append(("edge", os.path.join(local, "Microsoft", "Edge", "User Data")))
    out = []
    for browser, base in bases:
        if not os.path.isdir(base):
            continue
        profiles = ["Default"] + [d for d in os.listdir(base) if d.startswith("Profile ")]
        for profile in profiles:
            db = os.path.join(base, profile, "Login Data")
            if not os.path.exists(db):
                continue
            tmp = os.path.join(tempfile.gettempdir(), f"ca_{browser}_{profile.replace(' ', '_')}_login_data")
            try:
                shutil.copy2(db, tmp)
                con = sqlite3.connect(tmp)
                cur = con.execute("select origin_url, action_url, username_value, password_value, blacklisted_by_user from logins")
                for origin_url, action_url, username, password_blob, blacklisted in cur.fetchall():
                    item = {"source": browser, "profile": profile, "origin_url": origin_url, "action_url": action_url, "username": username, "blacklisted": bool(blacklisted), "secret": None}
                    blob = json.dumps(item, ensure_ascii=False).lower()
                    if query_l and query_l not in blob:
                        continue
                    if reveal:
                        item["secret"] = _dpapi_decrypt(password_blob)
                    out.append(item)
                    if len(out) >= limit:
                        return out
                con.close()
            except Exception as e:
                out.append({"source": browser, "profile": profile, "error": str(e)})
            finally:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
    return out

def _dpapi_decrypt(blob) -> str | None:
    try:
        import ctypes
        from ctypes import wintypes
        if blob is None:
            return None
        data = bytes(blob)
        if data.startswith(b"v10") or data.startswith(b"v11"):
            return "[chrome password encrypted with app-bound/AES key; Local State key support pendiente]"

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        in_buf = ctypes.create_string_buffer(data)
        in_blob = DATA_BLOB(len(data), ctypes.cast(in_buf, ctypes.POINTER(ctypes.c_char)))
        out_blob = DATA_BLOB()
        if not crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
            return None
        try:
            raw = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            return raw.decode("utf-8", errors="replace")
        finally:
            kernel32.LocalFree(out_blob.pbData)
    except Exception as e:
        return f"[decrypt error: {e}]"

def _clipboard_read() -> dict:
    r = _shell("Get-Clipboard", "powershell")
    return {"clipboard": r.get("stdout", ""), "length": len(r.get("stdout",""))}

def _clipboard_write(text: str) -> dict:
    import base64 as _b64
    encoded = _b64.b64encode(text.encode("utf-16-le")).decode("ascii")
    r = _shell(
        f'[System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String("{encoded}")) | Set-Clipboard',
        "powershell"
    )
    return {"ok": r.get("returncode") == 0, "length": len(text)}

def _http_request(url: str, method: str = "GET", headers: dict = None,
                  body: str = "", timeout: int = 30) -> dict:
    import urllib.request, urllib.error
    safe, reason = _is_safe_external_url(url)
    if not safe:
        return {"error": f"URL bloqueada por política de seguridad: {reason}"}
    headers = headers or {}
    req = urllib.request.Request(url, method=method.upper())
    for k, v in headers.items():
        req.add_header(k, v)
    data = body.encode() if body else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            return {"status": resp.status, "headers": dict(resp.headers),
                    "body": content[:10000], "truncated": len(content) > 10000}
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="replace")
        return {"status": e.code, "error": str(e), "body": body_err[:2000]}
    except Exception as e:
        return {"error": str(e)}

def _search_files(path: str, pattern: str = "*", content: str = "",
                  recursive: bool = True, max_results: int = 50) -> dict:
    path = os.path.expandvars(os.path.expanduser(path))
    results = []
    walk = os.walk(path) if recursive else [(path, [], os.listdir(path))]
    for root, dirs, files in walk:
        # Skip hidden/system dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                   ('node_modules', '__pycache__', '.git', 'venv', '.venv')]
        for fname in files:
            if fnmatch.fnmatch(fname.lower(), pattern.lower()):
                fpath = os.path.join(root, fname)
                if not os.path.isfile(fpath):
                    continue
                if content:
                    try:
                        with open(fpath, encoding="utf-8", errors="replace") as _fh:
                            text = _fh.read(200000)
                        if content.lower() in text.lower():
                            line_no = next((i+1 for i,l in enumerate(text.splitlines())
                                           if content.lower() in l.lower()), None)
                            results.append({"path": fpath, "match_line": line_no})
                    except Exception:
                        pass
                else:
                    results.append({"path": fpath, "size": os.path.getsize(fpath)})
        if len(results) >= max_results:
            break
    return {"results": results[:max_results], "count": len(results),
            "truncated": len(results) >= max_results}

def _kill_process(name: str = "", pid: int = None, force: bool = True) -> dict:
    killed = []
    errors = []
    import psutil
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if pid and proc.info['pid'] == pid:
                proc.kill() if force else proc.terminate()
                killed.append(f"{proc.info['name']} (PID {pid})")
            elif name and name.lower() in proc.info['name'].lower():
                proc.kill() if force else proc.terminate()
                killed.append(f"{proc.info['name']} (PID {proc.info['pid']})")
        except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(str(e))
    return {"killed": killed, "errors": errors, "count": len(killed)}

def _gpu_info() -> dict:
    r = _shell("nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,"
               "utilization.memory,memory.used,memory.free,memory.total,"
               "power.draw,power.limit --format=csv,noheader,nounits", "powershell")
    if r.get("returncode") == 0 and r.get("stdout"):
        parts = [p.strip() for p in r["stdout"].split(",")]
        labels = ["name","temp_c","gpu_util_%","mem_util_%",
                  "mem_used_mb","mem_free_mb","mem_total_mb","power_w","power_limit_w"]
        info = dict(zip(labels, parts))
        # Also get processes using GPU
        proc_r = _shell("nvidia-smi --query-compute-apps=pid,name,used_memory "
                        "--format=csv,noheader", "powershell")
        info["gpu_processes"] = proc_r.get("stdout", "")
        return info
    return {"error": "nvidia-smi no disponible o GPU no detectada"}

def _open_browser(url: str) -> dict:
    import webbrowser
    webbrowser.open(url)
    return {"ok": True, "url": url}

def _windows_notify(title: str, message: str) -> dict:
    script = (
        f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
        f"ContentType = WindowsRuntime] | Out-Null; "
        f"$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
        f"[Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
        f"$t.SelectSingleNode('//text[@id=1]').InnerText = '{title.replace(chr(39), chr(39)*2)}'; "
        f"$t.SelectSingleNode('//text[@id=2]').InnerText = '{message.replace(chr(39), chr(39)*2)}'; "
        f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('CyberAgent')"
        f".Show([Windows.UI.Notifications.ToastNotification]::new($t))"
    )
    r = _shell(script, "powershell")
    return {"ok": r.get("returncode") == 0}

def _hash_file(path: str, algorithm: str = "sha256") -> dict:
    path = os.path.expandvars(os.path.expanduser(path))
    if not os.path.exists(path):
        return {"error": f"No encontrado: {path}"}
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return {"path": path, "algorithm": algorithm, "hash": h.hexdigest(),
            "size": os.path.getsize(path)}

def _diff_files(file_a: str, file_b: str) -> dict:
    for p in (file_a, file_b):
        if not os.path.exists(p):
            return {"error": f"No encontrado: {p}"}
    with open(file_a, encoding="utf-8", errors="replace") as _fa:
        lines_a = _fa.readlines()
    with open(file_b, encoding="utf-8", errors="replace") as _fb:
        lines_b = _fb.readlines()
    diff = list(difflib.unified_diff(lines_a, lines_b,
                                     fromfile=file_a, tofile=file_b, lineterm=""))
    return {"diff": "".join(diff[:200]), "lines_changed": len(diff),
            "truncated": len(diff) > 200}

def _encode_decode(text: str, operation: str) -> dict:
    ops = {
        "base64_encode": lambda t: base64.b64encode(t.encode()).decode(),
        "base64_decode": lambda t: base64.b64decode(t).decode("utf-8", errors="replace"),
        "url_encode":    lambda t: urllib.parse.quote(t),
        "url_decode":    lambda t: urllib.parse.unquote(t),
        "hex_encode":    lambda t: t.encode().hex(),
        "hex_decode":    lambda t: bytes.fromhex(t).decode("utf-8", errors="replace"),
        "rot13":         lambda t: codecs.encode(t, "rot_13"),
    }
    fn = ops.get(operation)
    if not fn:
        return {"error": f"Operación desconocida: {operation}"}
    try:
        return {"result": fn(text), "operation": operation}
    except Exception as e:
        return {"error": str(e)}

def _network_info(section: str = "all") -> dict:
    result = {}
    if section in ("all", "interfaces"):
        r = _shell("Get-NetIPAddress | Select-Object InterfaceAlias,IPAddress,AddressFamily | ConvertTo-Json", "powershell")
        result["interfaces"] = r.get("stdout", "")
    if section in ("all", "connections"):
        r = _shell("netstat -ano | Select-Object -First 40", "powershell")
        result["connections"] = r.get("stdout", "")
    if section in ("all", "routes"):
        r = _shell("Get-NetRoute | Select-Object DestinationPrefix,NextHop,RouteMetric | ConvertTo-Json", "powershell")
        result["routes"] = r.get("stdout", "")
    if section in ("all", "dns"):
        r = _shell("Get-DnsClientServerAddress | ConvertTo-Json", "powershell")
        result["dns"] = r.get("stdout", "")
    return result

def _env_vars(action: str, name: str = "", value: str = "", scope: str = "process") -> dict:
    scope_map = {"process": "Process", "user": "User", "machine": "Machine"}
    s = scope_map.get(scope, "Process")
    if action == "list":
        r = _shell("Get-ChildItem Env: | Select-Object Name,Value | ConvertTo-Json", "powershell")
        return {"vars": r.get("stdout", "")}
    elif action == "get":
        _n = name.replace("'", "''")
        r = _shell(f"[System.Environment]::GetEnvironmentVariable('{_n}', '{s}')", "powershell")
        return {"name": name, "value": r.get("stdout", "").strip()}
    elif action == "set":
        _n = name.replace("'", "''"); _v = value.replace("'", "''")
        r = _shell(f"[System.Environment]::SetEnvironmentVariable('{_n}', '{_v}', '{s}')", "powershell")
        return {"ok": r.get("returncode") == 0, "name": name}
    elif action == "delete":
        _n = name.replace("'", "''")
        r = _shell(f"[System.Environment]::SetEnvironmentVariable('{_n}', $null, '{s}')", "powershell")
        return {"ok": r.get("returncode") == 0, "name": name}
    return {"error": f"Acción desconocida: {action}"}

def _memory_info(top_n: int = 10) -> dict:
    try:
        import psutil
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
        procs = sorted(
            [{"pid": p.info["pid"], "name": p.info["name"],
              "mem_mb": round(p.info["memory_info"].rss / 1024**2, 1)}
             for p in psutil.process_iter(["pid", "name", "memory_info"])
             if p.info.get("memory_info")],
            key=lambda x: x["mem_mb"], reverse=True
        )[:top_n]
        return {
            "total_gb":     round(vm.total / 1024**3, 2),
            "available_gb": round(vm.available / 1024**3, 2),
            "used_pct":     vm.percent,
            "swap_used_gb": round(sw.used / 1024**3, 2),
            "top_consumers": procs,
        }
    except Exception as e:
        return {"error": str(e)}


def _web_search(query: str, max_results: int = 5) -> dict:
    """Busca en DuckDuckGo HTML (sin API key)."""
    import re as _re
    max_results = min(int(max_results), 10)
    try:
        import httpx
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        }
        r = httpx.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "kl": "es-ES"},
            headers=headers,
            timeout=20,
            follow_redirects=True,
        )
        html = r.text
        def clean(s):
            s = _re.sub(r'<[^>]+>', '', s)
            return s.strip().replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')

        titles   = [clean(m) for m in _re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, _re.DOTALL)]
        snippets = [clean(m) for m in _re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, _re.DOTALL)]
        urls_raw = [clean(m) for m in _re.findall(r'class="result__url"[^>]*>\s*(.*?)\s*</span>', html, _re.DOTALL)]

        results = []
        for i in range(min(max_results, len(titles))):
            results.append({
                "title":   titles[i],
                "snippet": snippets[i] if i < len(snippets) else "",
                "url":     urls_raw[i] if i < len(urls_raw) else "",
            })

        return {"query": query, "results": results, "count": len(results)}
    except Exception as e:
        return {"error": str(e), "query": query}


def _rag_search(query: str, n_results: int = 3) -> dict:
    try:
        from app.rag.vectorstore import search
        docs = search(query, n_results=n_results)
        return {"results": docs, "count": len(docs)}
    except Exception as e:
        return {"error": str(e)}


def _rag_add(title: str, content: str, tags: list = None, platform: str = "all") -> dict:
    try:
        from app.rag.vectorstore import add_document
        import hashlib as _hl
        doc_id = "learned_" + _hl.md5(title.encode()).hexdigest()[:12]
        add_document(doc_id, title, content, platform=platform, tags=tags or [])
        return {"ok": True, "id": doc_id, "title": title}
    except Exception as e:
        return {"error": str(e)}


# ── Reverse engineering / binary analysis ─────────────────────────────────────

def _strings_extract(path: str, min_length: int = 4) -> dict:
    path = os.path.expandvars(os.path.expanduser(path))
    if not os.path.exists(path):
        return {"error": f"No encontrado: {path}"}
    MAX_SIZE = 50 * 1024 * 1024
    size = os.path.getsize(path)
    if size > MAX_SIZE:
        return {"error": f"Archivo demasiado grande ({size // 1024 // 1024}MB > 50MB)"}
    PRINTABLE = set(range(0x20, 0x7f)) | {0x09, 0x0a, 0x0d}
    with open(path, "rb") as f:
        data = f.read()
    strings, current = [], []
    for b in data:
        if b in PRINTABLE:
            current.append(chr(b))
        else:
            if len(current) >= min_length:
                strings.append("".join(current))
            current = []
    if len(current) >= min_length:
        strings.append("".join(current))
    return {
        "path":      path,
        "file_size": size,
        "count":     len(strings),
        "strings":   strings[:500],
        "truncated": len(strings) > 500,
    }


def _hex_dump(path: str, offset: int = 0, length: int = 256) -> dict:
    path = os.path.expandvars(os.path.expanduser(path))
    if not os.path.exists(path):
        return {"error": f"No encontrado: {path}"}
    length = min(length, 4096)
    with open(path, "rb") as f:
        f.seek(offset)
        data = f.read(length)
    lines = []
    for i in range(0, len(data), 16):
        chunk    = data[i:i+16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        asc_part = "".join(chr(b) if 0x20 <= b < 0x7f else "." for b in chunk)
        lines.append(f"{offset+i:08x}  {hex_part:<47}  |{asc_part}|")
    return {
        "path":      path,
        "offset":    offset,
        "length":    len(data),
        "file_size": os.path.getsize(path),
        "hex_dump":  "\n".join(lines),
    }


def _file_entropy(path: str) -> dict:
    import math
    path = os.path.expandvars(os.path.expanduser(path))
    if not os.path.exists(path):
        return {"error": f"No encontrado: {path}"}
    size = os.path.getsize(path)
    if size > 100 * 1024 * 1024:
        return {"error": f"Archivo demasiado grande ({size // 1024 // 1024}MB > 100MB)"}

    def _entropy(buf: bytes) -> float:
        if not buf:
            return 0.0
        c = [0] * 256
        for b in buf:
            c[b] += 1
        n = len(buf)
        return -sum((x/n) * math.log2(x/n) for x in c if x)

    with open(path, "rb") as f:
        data = f.read()
    overall = _entropy(data)
    BLOCK   = 512
    sections = [
        {"offset": i, "entropy": round(_entropy(data[i:i+BLOCK]), 3)}
        for i in range(0, min(len(data), 64 * 1024), BLOCK)
    ]
    if overall > 7.8:
        interpretation = "muy alta — cifrado o comprimido"
    elif overall > 7.2:
        interpretation = "alta — posible packer"
    elif overall > 6.5:
        interpretation = "media-alta — puede contener datos binarios"
    elif overall < 3.0:
        interpretation = "baja — texto plano o datos con patrones"
    else:
        interpretation = "normal"
    return {
        "path":             path,
        "file_size":        size,
        "overall_entropy":  round(overall, 4),
        "interpretation":   interpretation,
        "sections_sample":  sections[:32],
    }


def _pe_info(path: str) -> dict:
    path = os.path.expandvars(os.path.expanduser(path))
    if not os.path.exists(path):
        return {"error": f"No encontrado: {path}"}
    try:
        import pefile
        pe = pefile.PE(path, fast_load=False)
        result = {
            "machine":      hex(pe.FILE_HEADER.Machine),
            "timestamp":    pe.FILE_HEADER.TimeDateStamp,
            "num_sections": pe.FILE_HEADER.NumberOfSections,
            "entry_point":  hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),
            "image_base":   hex(pe.OPTIONAL_HEADER.ImageBase),
            "subsystem":    pe.OPTIONAL_HEADER.Subsystem,
            "sections": [
                {"name": s.Name.decode("utf-8", "replace").rstrip("\x00"),
                 "virtual_size": s.Misc_VirtualSize,
                 "raw_size":     s.SizeOfRawData,
                 "characteristics": hex(s.Characteristics)}
                for s in pe.sections
            ],
        }
        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            result["imports"] = [
                {"dll": e.dll.decode("utf-8", "replace"),
                 "functions": [
                     imp.name.decode("utf-8", "replace") if imp.name else f"ord_{imp.ordinal}"
                     for imp in e.imports[:20]
                 ]}
                for e in pe.DIRECTORY_ENTRY_IMPORT[:20]
            ]
        if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
            result["exports"] = [
                exp.name.decode("utf-8", "replace") if exp.name else f"ord_{exp.ordinal}"
                for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols[:50]
            ]
        pe.close()
        return result
    except ImportError:
        # Pure Python fallback — parse PE header manually
        import struct
        with open(path, "rb") as f:
            data = f.read(4096)
        if len(data) < 64 or data[:2] != b"MZ":
            return {"error": "No es un ejecutable PE válido (sin cabecera MZ)"}
        pe_off = struct.unpack_from("<I", data, 0x3C)[0]
        if pe_off + 24 > len(data):
            return {"error": "Cabecera PE truncada"}
        if data[pe_off:pe_off+4] != b"PE\x00\x00":
            return {"error": f"Firma PE inválida: {data[pe_off:pe_off+4].hex()}"}
        machine, nsec, ts = struct.unpack_from("<HHI", data, pe_off + 4)
        ep         = struct.unpack_from("<I", data, pe_off + 40)[0]
        imagebase  = struct.unpack_from("<I", data, pe_off + 52)[0]
        machines   = {0x14c: "x86", 0x8664: "x64", 0xaa64: "ARM64", 0x1c4: "ARMv7"}
        return {
            "machine":      machines.get(machine, hex(machine)),
            "num_sections": nsec,
            "timestamp":    ts,
            "entry_point":  hex(ep),
            "image_base":   hex(imagebase),
            "note":         "pip install pefile para análisis completo de imports/exports",
        }
    except Exception as e:
        return {"error": str(e)}


def _file_metadata(path: str) -> dict:
    path = os.path.expandvars(os.path.expanduser(path))
    if not os.path.exists(path):
        return {"error": f"No encontrado: {path}"}
    stat = os.stat(path)
    with open(path, "rb") as f:
        magic_raw = f.read(16)
    magic_hex = magic_raw.hex()
    MAGIC = {
        "504b0304": "ZIP archive",
        "4d5a":     "Windows PE/MZ executable",
        "7f454c46": "ELF executable",
        "cafebabe": "Java class / Mach-O fat binary",
        "25504446": "PDF document",
        "d0cf11e0": "MS Office (legacy OLE)",
        "89504e47": "PNG image",
        "ffd8ff":   "JPEG image",
        "52617221": "RAR archive",
        "377abcaf": "7-Zip archive",
        "1f8b08":   "Gzip compressed",
        "7573746172": "TAR archive",
        "4d546864": "MIDI audio",
        "494433":   "MP3 (ID3 tag)",
        "424d":     "BMP image",
    }
    detected = "unknown"
    for sig, name in MAGIC.items():
        if magic_hex.startswith(sig):
            detected = name
            break
    h_md5, h_sha256 = hashlib.md5(), hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h_md5.update(chunk)
            h_sha256.update(chunk)
    result = {
        "path":          path,
        "size":          stat.st_size,
        "created":       datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
        "modified":      datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "accessed":      datetime.fromtimestamp(stat.st_atime).strftime("%Y-%m-%d %H:%M:%S"),
        "magic_bytes":   magic_hex[:16],
        "detected_type": detected,
        "md5":           h_md5.hexdigest(),
        "sha256":        h_sha256.hexdigest(),
    }
    if os.name == "nt":
        r = _shell(
            f"$f='{path.replace(chr(39), chr(39)+chr(39))}'; "
            "(Get-Item $f -ErrorAction SilentlyContinue).VersionInfo | ConvertTo-Json",
            "powershell",
        )
        if r.get("returncode") == 0 and r.get("stdout", "").strip():
            result["version_info"] = r["stdout"].strip()[:800]
        r2 = _shell(
            f"Get-AuthenticodeSignature '{path.replace(chr(39), chr(39)+chr(39))}' | "
            "Select-Object Status,StatusMessage | ConvertTo-Json",
            "powershell",
        )
        if r2.get("returncode") == 0:
            result["signature"] = r2["stdout"].strip()
    return result


# ── Advanced file search ───────────────────────────────────────────────────────

def _grep_files(directory: str, pattern: str, file_glob: str = "*",
                recursive: bool = True, context_lines: int = 2,
                max_results: int = 50) -> dict:
    import re as _re
    directory = os.path.expandvars(os.path.expanduser(directory))
    if not os.path.isdir(directory):
        return {"error": f"No es un directorio: {directory}"}
    try:
        regex = _re.compile(pattern, _re.IGNORECASE | _re.MULTILINE)
    except _re.error as e:
        return {"error": f"Regex inválida: {e}"}
    results = []
    SKIP_DIRS = {"node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build"}
    walk = os.walk(directory) if recursive else [(directory, [], os.listdir(directory))]
    for root, dirs, files in walk:
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if not fnmatch.fnmatch(fname.lower(), file_glob.lower()):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8", errors="replace") as _fh:
                    content = _fh.read(500_000)
            except Exception:
                continue
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if regex.search(line):
                    start = max(0, i - context_lines)
                    end   = min(len(lines), i + context_lines + 1)
                    ctx   = "\n".join(
                        f"{'>' if j == i else ' '} {j+1}: {lines[j]}"
                        for j in range(start, end)
                    )
                    results.append({"file": fpath, "line": i + 1,
                                    "match": line.strip()[:200], "context": ctx})
                    if len(results) >= max_results:
                        return {"results": results, "count": len(results), "truncated": True}
    return {"results": results, "count": len(results), "truncated": False}


# ── Windows security auditing ─────────────────────────────────────────────────

def _registry_query(key: str, value: str = "") -> dict:
    if value:
        cmd = (f"(Get-ItemProperty -Path 'Registry::{key}' "
               f"-Name '{value}' -ErrorAction Stop).'{value}'")
    else:
        cmd = f"Get-ItemProperty -Path 'Registry::{key}' -ErrorAction Stop | ConvertTo-Json -Depth 2"
    r = _shell(cmd, "powershell")
    if r.get("returncode") != 0:
        return {"error": r.get("stderr", "Clave no encontrada")[:500], "key": key}
    return {"key": key, "value_name": value or "(all)", "result": r.get("stdout", "").strip()}


def _list_services(state: str = "all", name_filter: str = "") -> dict:
    filter_state = {
        "running": "Where-Object { $_.Status -eq 'Running' }",
        "stopped": "Where-Object { $_.Status -eq 'Stopped' }",
    }.get(state, "Where-Object { $true }")
    _nf = name_filter.replace("'", "''")
    name_extra = f" | Where-Object {{ $_.Name -like '*{_nf}*' }}" if _nf else ""
    cmd = (f"Get-Service | {filter_state}{name_extra} | "
           "Select-Object Name,DisplayName,Status,StartType | ConvertTo-Json")
    r = _shell(cmd, "powershell")
    return {"services": r.get("stdout", "")[:8000], "state_filter": state}


def _check_persistence() -> dict:
    results = {}
    for short, key in [
        ("HKLM_Run",     r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        ("HKCU_Run",     r"HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        ("HKLM_RunOnce", r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
        ("HKLM_Run_WOW", r"HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
    ]:
        r = _shell(f"Get-ItemProperty 'Registry::{key}' -ErrorAction SilentlyContinue | ConvertTo-Json",
                   "powershell")
        results[short] = r.get("stdout", "").strip()[:2000]

    r = _shell("Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' } | "
               "Select-Object TaskName,TaskPath,State,Description | ConvertTo-Json", "powershell")
    results["scheduled_tasks"] = r.get("stdout", "")[:4000]

    r = _shell("Get-ChildItem '$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup' "
               "-ErrorAction SilentlyContinue | Select-Object Name,FullName | ConvertTo-Json",
               "powershell")
    results["startup_folder_user"] = r.get("stdout", "").strip()

    r = _shell("Get-ChildItem 'C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup' "
               "-ErrorAction SilentlyContinue | Select-Object Name,FullName | ConvertTo-Json",
               "powershell")
    results["startup_folder_all"] = r.get("stdout", "").strip()

    r = _shell("Get-Service | Where-Object { $_.StartType -eq 'Automatic' } | "
               "Select-Object Name,DisplayName,Status | ConvertTo-Json", "powershell")
    results["auto_services"] = r.get("stdout", "")[:3000]

    return results


def _network_connections(state: str = "all") -> dict:
    filter_state = {
        "listening":   "Where-Object { $_.State -eq 'Listen' }",
        "established": "Where-Object { $_.State -eq 'Established' }",
    }.get(state, "Where-Object { $true }")
    cmd = (
        f"Get-NetTCPConnection | {filter_state} | "
        "ForEach-Object { "
        "  $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
        "  [PSCustomObject]@{ "
        "    LocalAddress=$_.LocalAddress; LocalPort=$_.LocalPort; "
        "    RemoteAddress=$_.RemoteAddress; RemotePort=$_.RemotePort; "
        "    State=$_.State; PID=$_.OwningProcess; "
        "    Process=if($p){$p.Name}else{'?'} "
        "  } "
        "} | ConvertTo-Json"
    )
    r = _shell(cmd, "powershell")
    return {"connections": r.get("stdout", "")[:8000], "filter": state}


def _process_tree() -> dict:
    try:
        import psutil
        procs = {}
        for p in psutil.process_iter(["pid", "name", "ppid", "memory_info", "status"]):
            try:
                info = p.info
                procs[info["pid"]] = {
                    "pid":      info["pid"],
                    "name":     info["name"],
                    "ppid":     info["ppid"],
                    "mem_mb":   round(info["memory_info"].rss / 1024**2, 1)
                                if info.get("memory_info") else 0,
                    "status":   info.get("status", "?"),
                    "children": [],
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        roots = []
        for pid, info in procs.items():
            ppid = info["ppid"]
            if ppid in procs and ppid != pid:
                procs[ppid]["children"].append(info)
            else:
                roots.append(info)

        def sort_tree(nodes):
            nodes.sort(key=lambda x: x["name"].lower())
            for n in nodes:
                sort_tree(n["children"])
        sort_tree(roots)
        return {"tree": roots[:200], "total": len(procs)}
    except Exception as e:
        return {"error": str(e)}


def _process_info(pid: int = None, name: str = "") -> dict:
    try:
        import psutil
        proc = None
        if pid:
            proc = psutil.Process(int(pid))
        elif name:
            for p in psutil.process_iter(["pid", "name"]):
                if name.lower() in p.info["name"].lower():
                    proc = psutil.Process(p.info["pid"])
                    break
        if proc is None:
            return {"error": "Proceso no encontrado"}
        with proc.oneshot():
            try:
                _exe = proc.exe() or "?"
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                _exe = "?"
            try:
                _cwd = proc.cwd() or "?"
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                _cwd = "?"
            result = {
                "pid":        proc.pid,
                "name":       proc.name(),
                "exe":        _exe,
                "cmdline":    " ".join(proc.cmdline()),
                "cwd":        _cwd,
                "status":     proc.status(),
                "username":   proc.username(),
                "created":    datetime.fromtimestamp(proc.create_time()).strftime("%Y-%m-%d %H:%M:%S"),
                "mem_mb":     round(proc.memory_info().rss / 1024**2, 1),
                "cpu_pct":    proc.cpu_percent(interval=0.1),
                "threads":    proc.num_threads(),
                "ppid":       proc.ppid(),
            }
            try:
                result["open_files"] = [f.path for f in proc.open_files()[:20]]
            except psutil.AccessDenied:
                result["open_files"] = ["access_denied"]
            try:
                result["connections"] = [
                    {"local": f"{c.laddr.ip}:{c.laddr.port}",
                     "remote": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "-",
                     "status": c.status}
                    for c in proc.connections()[:10]
                ]
            except psutil.AccessDenied:
                result["connections"] = ["access_denied"]
            try:
                result["modules"] = [m.path for m in proc.memory_maps()[:30]]
            except Exception:
                pass
        return result
    except psutil.NoSuchProcess:
        return {"error": f"Proceso {pid or name} no existe"}
    except Exception as e:
        return {"error": str(e)}


def _port_scan(host: str, ports: str = "1-1024", timeout: float = 0.5) -> dict:
    import socket, concurrent.futures
    port_list = []
    for part in ports.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            port_list.extend(range(int(a), int(b) + 1))
        else:
            port_list.append(int(part))
    if len(port_list) > 10000:
        return {"error": "Máximo 10.000 puertos por scan"}

    def check(port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                if s.connect_ex((host, port)) == 0:
                    try:
                        svc = socket.getservbyport(port)
                    except Exception:
                        svc = "unknown"
                    return {"port": port, "service": svc}
        except Exception:
            pass
        return None

    open_ports = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
        for res in concurrent.futures.as_completed(ex.submit(check, p) for p in port_list):
            r = res.result()
            if r:
                open_ports.append(r)
    open_ports.sort(key=lambda x: x["port"])
    return {
        "host":          host,
        "ports_scanned": len(port_list),
        "open_ports":    open_ports,
        "count":         len(open_ports),
    }


# ── Web auditing ──────────────────────────────────────────────────────────────

def _ssl_info(host: str, port: int = 443) -> dict:
    import ssl, socket
    def _get_cert(verify: bool):
        ctx = ssl.create_default_context()
        if not verify:
            ctx.check_hostname = False
            ctx.verify_mode    = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                return ssock.getpeercert(), ssock.version(), ssock.cipher()
    try:
        cert, version, cipher = _get_cert(True)
        verified = True
    except ssl.SSLCertVerificationError as e:
        try:
            cert, version, cipher = _get_cert(False)
            verified = False
        except Exception as e2:
            return {"host": host, "port": port, "error": str(e2)}
    except Exception as e:
        return {"host": host, "port": port, "error": str(e)}

    subject = dict(x[0] for x in cert.get("subject", []))
    issuer  = dict(x[0] for x in cert.get("issuer", []))
    san     = cert.get("subjectAltName", [])
    return {
        "host":         host,
        "port":         port,
        "verified":     verified,
        "tls_version":  version,
        "cipher":       cipher[0] if cipher else "?",
        "bits":         cipher[2] if cipher and len(cipher) > 2 else "?",
        "subject_cn":   subject.get("commonName", "?"),
        "issuer_cn":    issuer.get("commonName", "?"),
        "issuer_org":   issuer.get("organizationName", "?"),
        "valid_from":   cert.get("notBefore"),
        "valid_until":  cert.get("notAfter"),
        "san":          [v for _, v in san],
        "serial":       cert.get("serialNumber"),
    }


_SECURITY_HEADERS = {
    "Strict-Transport-Security": "HSTS — fuerza HTTPS",
    "Content-Security-Policy":   "CSP — previene XSS/injection",
    "X-Frame-Options":           "Clickjacking protection",
    "X-Content-Type-Options":    "MIME sniffing protection",
    "Referrer-Policy":           "Referrer control",
    "Permissions-Policy":        "Browser features control",
    "X-XSS-Protection":          "Legacy XSS filter",
    "Access-Control-Allow-Origin": "CORS policy",
    "Cache-Control":             "Caching policy",
    "Cross-Origin-Opener-Policy": "COOP — cross-origin isolation",
}

def _http_headers_check(url: str) -> dict:
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CyberAgent-Audit/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_headers = {k.lower(): v for k, v in resp.headers.items()}
            status      = resp.status
    except Exception as e:
        return {"error": str(e), "url": url}

    present, missing = {}, []
    for h, desc in _SECURITY_HEADERS.items():
        val = raw_headers.get(h.lower())
        if val:
            present[h] = val
        else:
            missing.append({"header": h, "description": desc})

    # Extra checks
    warnings = []
    server = raw_headers.get("server", "")
    if server:
        warnings.append(f"Server header expuesto: {server}")
    powered = raw_headers.get("x-powered-by", "")
    if powered:
        warnings.append(f"X-Powered-By expuesto: {powered}")
    if "http://" in url and not raw_headers.get("strict-transport-security"):
        warnings.append("Sitio HTTP sin HSTS")

    score = round(len(present) / len(_SECURITY_HEADERS) * 100)
    return {
        "url":             url,
        "status_code":     status,
        "security_score":  f"{score}%  ({len(present)}/{len(_SECURITY_HEADERS)} headers)",
        "present_headers": present,
        "missing_headers": missing,
        "warnings":        warnings,
        "server":          server or "not disclosed",
        "x_powered_by":    powered or "not disclosed",
        "all_headers":     dict(raw_headers),
    }


def _web_crawl(url: str, depth: int = 1, max_links: int = 50) -> dict:
    import urllib.request, re as _re
    from urllib.parse import urljoin, urlparse

    visited     = set()
    links_found = []
    base_host   = urlparse(url).netloc

    def crawl(u: str, d: int):
        if u in visited or len(links_found) >= max_links or d < 0:
            return
        visited.add(u)
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "CyberAgent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                visited.add(resp.geturl())  # track post-redirect URL to avoid re-crawling
                ct = resp.headers.get("Content-Type", "")
                if "text/html" not in ct:
                    return
                html = resp.read().decode("utf-8", errors="replace")
        except Exception:
            return
        for href in _re.findall(r'href=["\']([^"\'#?][^"\']*)["\']', html, _re.IGNORECASE):
            full   = urljoin(u, href)
            parsed = urlparse(full)
            if parsed.scheme not in ("http", "https"):
                continue
            info = {"url": full, "same_origin": parsed.netloc == base_host}
            if full not in visited:
                links_found.append(info)
                if d > 0 and parsed.netloc == base_host:
                    crawl(full, d - 1)

    crawl(url, min(depth, 2))
    same   = [l for l in links_found if l["same_origin"]]
    extern = [l for l in links_found if not l["same_origin"]]
    return {
        "start_url":     url,
        "pages_visited": len(visited),
        "same_origin":   [l["url"] for l in same[:max_links]],
        "external":      [l["url"] for l in extern[:20]],
        "total_found":   len(links_found),
        "truncated":     len(links_found) >= max_links,
    }


_DIR_WORDLIST = [
    "admin","administrator","login","wp-admin","phpmyadmin","dashboard","panel","cpanel",
    "backup","backups",".git",".env","config","conf","configuration","settings",
    "api","v1","v2","v3","graphql","swagger","openapi","docs","api-docs","redoc",
    "robots.txt","sitemap.xml","security.txt",".well-known","crossdomain.xml",
    "upload","uploads","files","file","static","assets","img","images","media",
    "test","dev","development","staging","beta","old","bak","backup.zip","dump.sql",
    "temp","tmp","cache","logs","log","debug","trace","error","errors",
    "user","users","account","accounts","profile","register","signup","auth","oauth",
    "search","ajax","data","json","xml","feed","rss",
    "shell","cmd","exec","phpinfo.php","info.php","server-status","server-info",
    "wp-config.php","web.config",".htaccess","web.xml","applicationHost.config",
    "actuator","actuator/health","actuator/env","actuator/metrics","health","metrics","status",
    "console","manager","management","monitoring","grafana","kibana","jenkins",
]

def _dir_bruteforce(url: str, wordlist: str = "common", timeout: float = 5.0,
                    max_workers: int = 20) -> dict:
    import urllib.request, urllib.error, concurrent.futures
    url   = url.rstrip("/")
    words = _DIR_WORDLIST if wordlist == "common" else wordlist.split(",")

    found = []

    def check(word: str):
        target = f"{url}/{word.strip()}"
        try:
            req = urllib.request.Request(
                target, headers={"User-Agent": "CyberAgent-Audit/1.0"}, method="GET"
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return {"url": target, "status": r.status,
                        "content_length": r.headers.get("Content-Length", "?")}
        except urllib.error.HTTPError as e:
            if e.code not in (404, 410):
                return {"url": target, "status": e.code}
        except Exception:
            pass
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for res in concurrent.futures.as_completed(ex.submit(check, w) for w in words):
            r = res.result()
            if r:
                found.append(r)

    found.sort(key=lambda x: x["status"])
    return {
        "target":        url,
        "words_checked": len(words),
        "found":         found,
        "count":         len(found),
    }


# ── Network auditing ──────────────────────────────────────────────────────────

def _dns_lookup(hostname: str, record_type: str = "A") -> dict:
    import re as _re
    if not _re.fullmatch(r"[A-Za-z0-9.\-]+", hostname):
        return {"error": "hostname inválido"}
    record_type = record_type.upper()
    if record_type not in {"A","AAAA","MX","TXT","NS","CNAME","SOA","PTR","ANY"}:
        record_type = "A"
    try:
        import dns.resolver
        answers = dns.resolver.resolve(hostname, record_type)
        return {
            "hostname":    hostname,
            "record_type": record_type,
            "records":     [str(r) for r in answers],
            "ttl":         answers.rrset.ttl,
        }
    except ImportError:
        pass
    # Fallback: nslookup via shell (hostname already validated above)
    r = _shell(f"nslookup -type={record_type} {hostname} 2>&1", "cmd", timeout=15)
    return {
        "hostname":    hostname,
        "record_type": record_type,
        "raw_output":  (r.get("stdout", "") + r.get("stderr", ""))[:3000],
        "note":        "pip install dnspython para resultados estructurados",
    }


def _whois_lookup(domain: str) -> dict:
    import socket, re as _re
    tld = domain.rsplit(".", 1)[-1].lower()
    SERVERS = {
        "com":"whois.verisign-grs.com","net":"whois.verisign-grs.com",
        "org":"whois.pir.org","io":"whois.nic.io","es":"whois.nic.es",
        "co":"whois.nic.co","uk":"whois.nic.uk","de":"whois.denic.de",
        "fr":"whois.nic.fr","dev":"whois.nic.google","app":"whois.nic.google",
        "info":"whois.afilias.net","biz":"whois.biz","mobi":"whois.dotmobiregistry.net",
    }
    server = SERVERS.get(tld, "whois.iana.org")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(15)
            s.connect((server, 43))
            s.sendall(f"{domain}\r\n".encode())
            chunks = []
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        text = b"".join(chunks).decode("utf-8", errors="replace")
        result = {"domain": domain, "whois_server": server}
        for field, patterns in {
            "registrar":    ["Registrar:","Registrar Name:"],
            "created":      ["Creation Date:","created:","Registered:","Created On:"],
            "updated":      ["Updated Date:","last-modified:","Last Updated On:"],
            "expires":      ["Registry Expiry Date:","Expiry Date:","Expiration Date:"],
            "name_servers": ["Name Server:","nserver:"],
            "status":       ["Domain Status:","Status:"],
            "registrant":   ["Registrant Name:","Registrant Organization:"],
        }.items():
            for pat in patterns:
                matches = _re.findall(rf"(?i){_re.escape(pat)}\s*(.+)", text)
                if matches:
                    vals = [m.strip() for m in matches[:5]]
                    result[field] = vals if len(vals) > 1 else vals[0]
                    break
        result["raw"] = text[:4000]
        return result
    except Exception as e:
        return {"domain": domain, "error": str(e)}


def _traceroute(host: str, max_hops: int = 30) -> dict:
    import re as _re
    if not _re.fullmatch(r"[A-Za-z0-9.\-]+", host):
        return {"error": "host inválido"}
    max_hops = max(1, min(int(max_hops), 64))
    r = _shell(f"tracert -d -h {max_hops} {host}", "cmd", timeout=90)
    return {
        "host":   host,
        "output": (r.get("stdout", "") + r.get("stderr", ""))[:6000],
    }


def _banner_grab(host: str, port: int, timeout: float = 3.0) -> dict:
    import socket
    PROBES = {
        80:   b"HEAD / HTTP/1.0\r\nHost: " + host.encode() + b"\r\n\r\n",
        8080: b"HEAD / HTTP/1.0\r\nHost: " + host.encode() + b"\r\n\r\n",
        443:  b"HEAD / HTTP/1.0\r\nHost: " + host.encode() + b"\r\n\r\n",
        25:   None,   # SMTP sends banner on connect
        21:   None,   # FTP sends banner on connect
        22:   None,   # SSH sends banner on connect
        110:  None,   # POP3
        143:  None,   # IMAP
    }
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            probe = PROBES.get(port, b"\r\n")
            if probe:
                s.sendall(probe)
            banner = b""
            while True:
                try:
                    chunk = s.recv(2048)
                    if not chunk:
                        break
                    banner += chunk
                    if len(banner) > 4096:
                        break
                except socket.timeout:
                    break
        return {
            "host":   host,
            "port":   port,
            "banner": banner.decode("utf-8", errors="replace").strip()[:2000],
            "bytes":  len(banner),
        }
    except Exception as e:
        return {"host": host, "port": port, "error": str(e)}


def _ping_sweep(network: str, timeout_ms: int = 500) -> dict:
    import ipaddress, concurrent.futures
    hosts = []
    if "/" in network:
        try:
            net   = ipaddress.ip_network(network, strict=False)
            hosts = [str(ip) for ip in net.hosts()]
        except ValueError as e:
            return {"error": str(e)}
    elif "-" in network:
        base, end = network.rsplit("-", 1)
        parts     = base.split(".")
        for i in range(int(parts[-1]), int(end) + 1):
            hosts.append(".".join(parts[:-1] + [str(i)]))
    else:
        hosts = [network]

    if len(hosts) > 256:
        return {"error": "Máximo 256 hosts por sweep"}

    def ping(ip: str):
        try:
            r = subprocess.run(
                ["ping", "-n", "1", "-w", str(timeout_ms), ip],
                capture_output=True, text=True,
                timeout=timeout_ms / 1000 + 2,
            )
            if r.returncode == 0:
                return ip
        except Exception:
            pass
        return None

    alive = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as ex:
        for res in concurrent.futures.as_completed(ex.submit(ping, h) for h in hosts):
            ip = res.result()
            if ip:
                alive.append(ip)
    try:
        alive.sort(key=lambda ip: tuple(int(x) for x in ip.split(".")))
    except Exception:
        alive.sort()
    return {
        "network":      network,
        "hosts_probed": len(hosts),
        "alive":        alive,
        "count":        len(alive),
    }


def _arp_cache() -> dict:
    r = _shell("arp -a", "cmd")
    return {"arp_table": r.get("stdout", "")[:5000]}
