"""
Panel de Referencias y Permisos
Dialogo flotante con:
  - Búsqueda de comandos por categoría
  - Snippets de código listos para insertar en Chat o Terminal
  - Control de permisos por herramienta
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QTabWidget,
    QWidget, QTextEdit, QSplitter,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

# ── Base de datos de comandos ──────────────────────────────────────────────

REFERENCES = {
    "Windows — PowerShell": [
        # (titulo, comando, descripción)
        ("Listar procesos RAM",       "Get-Process | Sort-Object WorkingSet -Descending | Select -First 20 | Format-Table -Auto",   "Top 20 procesos por uso de memoria"),
        ("Matar proceso por nombre",  "Stop-Process -Name 'notepad' -Force",                                                         "Terminar proceso por nombre"),
        ("Listar servicios activos",  "Get-Service | Where-Object {$_.Status -eq 'Running'} | Format-Table -Auto",                  "Servicios en ejecución"),
        ("Puertos en escucha",        "netstat -ano | findstr LISTENING",                                                             "Ver puertos TCP/UDP abiertos"),
        ("Conexiones establecidas",   "Get-NetTCPConnection | Where-Object State -eq 'Established' | Select Local*,Remote*,State",   "Conexiones TCP activas"),
        ("Info hardware completa",    "Get-CimInstance Win32_Processor | Select Name,NumberOfCores; Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum; Get-CimInstance Win32_VideoController | Select Name,AdapterRAM", "CPU + RAM + GPU"),
        ("Ver IPs y adaptadores",     "Get-NetIPAddress | Select InterfaceAlias,IPAddress,PrefixLength | Format-Table -Auto",        "Adaptadores de red y sus IPs"),
        ("Reglas firewall activas",   "Get-NetFirewallRule | Where-Object Enabled -eq True | Select DisplayName,Direction,Action | Format-Table -Auto", "Reglas de firewall habilitadas"),
        ("Historial PowerShell",      "Get-History | Format-Table -Auto",                                                            "Ver historial de comandos recientes"),
        ("Buscar en registro",        "Get-ChildItem -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run'",              "Claves de autoarranque del sistema"),
        ("Usuarios locales",          "Get-LocalUser | Select Name,Enabled,LastLogon | Format-Table -Auto",                          "Listar cuentas de usuario"),
        ("Eventos de seguridad",      "Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4625} -MaxEvents 20 | Select TimeCreated,Message", "Logins fallidos (ID 4625)"),
        ("Uptime del sistema",        "(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime",                         "Tiempo desde el último arranque"),
        ("Espacio en discos",         "Get-PSDrive -PSProvider FileSystem | Select Name,Used,Free | Format-Table -Auto",             "Uso de espacio por unidad"),
        ("Abrir puerto en firewall",  "New-NetFirewallRule -DisplayName 'Puerto 8080' -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow", "Abrir puerto TCP 8080"),
        ("Tareas programadas",        "Get-ScheduledTask | Where-Object State -eq 'Ready' | Select TaskName,TaskPath | Format-Table -Auto", "Ver tareas programadas activas"),
        ("Variables de entorno",      "[System.Environment]::GetEnvironmentVariables('Machine') | Format-Table -Auto",               "Variables de entorno del sistema"),
        ("Exportar procesos CSV",     "Get-Process | Export-Csv -Path procesos.csv -NoTypeInformation",                              "Guardar lista de procesos en CSV"),
        ("Información del sistema",   "Get-ComputerInfo | Select WindowsProductName,TotalPhysicalMemory,CsProcessors",               "Resumen completo del sistema"),
        ("Flush DNS",                 "Clear-DnsClientCache; ipconfig /flushdns",                                                     "Limpiar caché DNS"),
    ],
    "Windows — CMD": [
        ("Ver IP y configuración",    "ipconfig /all",                                                 "Configuración completa de red"),
        ("Escanear red local",        "for /L %i in (1,1,254) do @ping -n 1 -w 100 192.168.1.%i | find 'Reply'", "Ping sweep red /24"),
        ("Ver puertos abiertos",      "netstat -ano",                                                  "Puertos TCP/UDP con PIDs"),
        ("Información del sistema",   "systeminfo",                                                    "Info detallada del sistema"),
        ("Usuarios del dominio",      "net user",                                                      "Listar usuarios locales"),
        ("Grupos locales",            "net localgroup",                                                "Listar grupos locales"),
        ("Shares de red",             "net share",                                                     "Carpetas compartidas"),
        ("Drivers instalados",        "driverquery",                                                   "Listar controladores"),
        ("Ver tareas programadas",    "schtasks /query /fo LIST",                                      "Tareas programadas (detallado)"),
        ("Ruta hasta un host",        "tracert google.com",                                            "Trazar ruta hasta destino"),
        ("Caché ARP",                 "arp -a",                                                        "Tabla ARP (IP→MAC)"),
        ("Copiar árbol de directorios","xcopy C:\\origen D:\\destino /E /I /H",                       "Copia recursiva con archivos ocultos"),
    ],
    "Linux — bash": [
        ("Top procesos CPU",          "ps aux --sort=-%cpu | head -15",                                "Top 15 procesos por CPU"),
        ("Top procesos RAM",          "ps aux --sort=-%mem | head -15",                                "Top 15 procesos por memoria"),
        ("Puertos en escucha",        "ss -tlnp",                                                     "Puertos TCP listening con proceso"),
        ("Conexiones activas",        "ss -tnp state established",                                    "Conexiones TCP establecidas"),
        ("Usuarios conectados",       "who && last | head -20",                                        "Usuarios activos y logins recientes"),
        ("Espacio en discos",         "df -h && du -sh /var/log/* 2>/dev/null | sort -rh | head -10", "Uso de disco y logs más pesados"),
        ("Buscar archivos grandes",   "find / -type f -size +100M 2>/dev/null | sort",                "Archivos mayores de 100MB"),
        ("Permisos SUID",             "find / -perm -4000 -type f 2>/dev/null",                       "Binarios con bit SUID (privesc)"),
        ("Contenido de /etc/passwd",  "cat /etc/passwd | grep -v nologin | grep -v false",            "Usuarios con shell válida"),
        ("Sudoers",                   "cat /etc/sudoers 2>/dev/null && cat /etc/sudoers.d/* 2>/dev/null", "Configuración de sudo"),
        ("Firewall estado",           "iptables -L -n -v 2>/dev/null || ufw status verbose",          "Reglas de firewall (iptables/ufw)"),
        ("Cronología de archivos",    "find /tmp /var/tmp -mmin -60 -type f 2>/dev/null",             "Archivos modificados en la última hora"),
        ("Servicio nginx/apache",     "systemctl status nginx apache2 2>/dev/null",                   "Estado de servidores web"),
        ("Ver logs del sistema",      "journalctl -n 50 --no-pager",                                  "Últimas 50 líneas del journal"),
        ("Captura tráfico",           "tcpdump -i any -c 100 -nn port 80 or port 443",               "Capturar 100 paquetes HTTP/HTTPS"),
        ("Ver variables entorno",     "printenv | sort",                                               "Variables de entorno del shell"),
        ("Instalar paquete (apt)",    "sudo apt update && sudo apt install -y <paquete>",             "Instalar en Debian/Ubuntu"),
        ("Instalar pip",              "pip install <paquete> --upgrade",                              "Instalar paquete Python"),
        ("Listar servicios",          "systemctl list-units --type=service --state=running",          "Servicios activos"),
        ("Información CPU/RAM",       "lscpu && free -h && cat /proc/meminfo | grep -E 'MemTotal|MemAvailable'", "Hardware del sistema"),
    ],
    "Seguridad — Reconocimiento": [
        ("Escaneo básico nmap",       "nmap -sV -T4 <IP>",                                            "Detección de servicios (rápido)"),
        ("Escaneo completo nmap",     "nmap -A -p- -T3 <IP>",                                        "Todos los puertos con detección OS"),
        ("Scripts de vulnerabilidades","nmap --script vuln <IP>",                                     "Detección básica de CVEs"),
        ("SMB vulnerabilidades",      "nmap --script smb-vuln* -p 445 <IP>",                         "Vulnerabilidades en SMB"),
        ("Red completa",              "nmap -sn 192.168.1.0/24",                                     "Hosts activos en la red"),
        ("DNS enumeration",           "nmap --script dns-brute <dominio>",                            "Fuerza bruta de subdominios"),
        ("Banner grabbing",           "nc -v <IP> <PUERTO>",                                          "Ver banner del servicio"),
        ("WhoIs dominio",             "whois <dominio>",                                              "Información del registrador"),
        ("Certificado SSL",           "openssl s_client -connect <host>:443 2>/dev/null | openssl x509 -text", "Detalles del certificado TLS"),
        ("Traceroute avanzado",       "mtr --report --report-cycles 5 <host>",                        "MTR con estadísticas de red"),
    ],
    "Seguridad — Web": [
        ("Directorio fuzzing",        "ffuf -w /usr/share/wordlists/dirb/common.txt -u http://TARGET/FUZZ -mc 200,301,302,403", "Descubrimiento de rutas web"),
        ("Nikto scan",                "nikto -h http://TARGET",                                       "Escáner de vulnerabilidades web"),
        ("Gobuster dirs",             "gobuster dir -u http://TARGET -w /usr/share/wordlists/dirb/common.txt -t 50", "Directorios con gobuster"),
        ("Subdominio fuzzing",        "ffuf -w subdomains.txt -u https://FUZZ.TARGET.com -mc 200",   "Descubrimiento de subdominios"),
        ("SQLmap básico",             "sqlmap -u 'http://target.com/page?id=1' --dbs --batch",        "Detección de SQLi"),
        ("Curl con headers",          "curl -I -L -A 'Mozilla/5.0' https://target.com",              "Ver headers de respuesta HTTP"),
        ("LFI test",                  "curl http://target.com/page?file=../../../../etc/passwd",      "Test de Local File Inclusion"),
        ("XSS básico",                "<script>alert(document.domain)</script>",                      "Payload XSS de prueba"),
        ("SSRF AWS metadata",         "http://169.254.169.254/latest/meta-data/",                    "Endpoint AWS metadata (SSRF target)"),
    ],
    "Python — Scripts": [
        ("Detectar OS",               "import platform; print(platform.system(), platform.version())", "Detectar sistema operativo"),
        ("Listar procesos",           "import psutil\nfor p in psutil.process_iter(['pid','name','memory_info']):\n    print(p.info['pid'], p.info['name'], round(p.info['memory_info'].rss/1e6,1), 'MB')", "Procesos con RAM"),
        ("Socket TCP cliente",        "import socket\ns=socket.socket()\ns.connect(('192.168.1.1',80))\ns.send(b'GET / HTTP/1.0\\r\\n\\r\\n')\nprint(s.recv(4096))\ns.close()", "Conexión TCP básica"),
        ("Port scan",                 "import socket\nopen_ports=[]\nfor p in range(1,1024):\n    s=socket.socket()\n    s.settimeout(0.5)\n    if not s.connect_ex(('127.0.0.1',p)):\n        open_ports.append(p)\n    s.close()\nprint(open_ports)", "Escaneo de puertos Python"),
        ("Leer JSON",                 "import json\nwith open('data.json') as f:\n    data=json.load(f)\nprint(data)", "Leer archivo JSON"),
        ("Request HTTP",              "import urllib.request\nr=urllib.request.urlopen('https://httpbin.org/ip')\nprint(r.read().decode())", "HTTP GET sin librerías externas"),
        ("Hash SHA256",               "import hashlib\nh=hashlib.sha256(open('archivo.txt','rb').read()).hexdigest()\nprint(h)", "Calcular hash de archivo"),
        ("Generar contraseña",        "import secrets,string\nalphabet=string.ascii_letters+string.digits+string.punctuation\npassword=''.join(secrets.choice(alphabet) for _ in range(20))\nprint(password)", "Contraseña segura aleatoria"),
        ("Escanear subred",           "import subprocess,ipaddress\nnet=ipaddress.ip_network('192.168.1.0/24')\nfor ip in net.hosts():\n    r=subprocess.run(['ping','-n','1','-w','200',str(ip)],capture_output=True)\n    if b'Reply' in r.stdout: print(ip)", "Ping sweep Python (Windows)"),
        ("Server HTTP simple",        "import http.server,socketserver\nwith socketserver.TCPServer(('',8000),http.server.SimpleHTTPRequestHandler) as h:\n    print('Servidor en :8000')\n    h.serve_forever()", "Servidor web de archivos :8000"),
    ],
    "Instalar paquetes": [
        ("pip instalar",              "pip install <paquete>",                                          "Instalar paquete Python"),
        ("pip actualizar",            "pip install --upgrade <paquete>",                               "Actualizar paquete Python"),
        ("pip listar instalados",     "pip list",                                                      "Paquetes Python instalados"),
        ("pip desinstalar",           "pip uninstall -y <paquete>",                                   "Desinstalar paquete Python"),
        ("winget instalar",           "winget install <nombre>",                                       "Instalar software con winget"),
        ("winget buscar",             "winget search <nombre>",                                        "Buscar software disponible"),
        ("winget actualizar todo",    "winget upgrade --all",                                          "Actualizar todo el software"),
        ("npm instalar global",       "npm install -g <paquete>",                                     "Instalar paquete Node.js global"),
        ("choco instalar",            "choco install <paquete> -y",                                   "Instalar con Chocolatey"),
        ("apt instalar (WSL)",        "sudo apt update && sudo apt install -y <paquete>",             "Instalar en Ubuntu/WSL"),
        ("pip de requirements.txt",   "pip install -r requirements.txt",                              "Instalar desde requirements"),
        ("pip requirements export",   "pip freeze > requirements.txt",                                "Exportar dependencias"),
    ],
    "Agente IA — Prompts": [
        ("Analizar sistema",          "Analiza mi sistema completo: OS, hardware, procesos activos, puertos en escucha y cualquier anomalía que detectes.", "Auditoría del sistema"),
        ("Escanear red local",        "Escanea la red local para encontrar todos los hosts activos. Usa nmap si está disponible.", "Reconocimiento de red"),
        ("Revisar logs",              "Revisa los logs de seguridad del sistema de las últimas 24 horas y reporta cualquier evento sospechoso.", "Análisis de logs"),
        ("Crear script Python",       "Crea un script Python que haga <tarea>. Guárdalo en el escritorio y ejecútalo.", "Automatizar tarea con Python"),
        ("Buscar vulnerabilidades",   "Analiza los servicios en escucha en este sistema y busca posibles vulnerabilidades conocidas.", "Auditoría de seguridad"),
        ("Configurar servidor web",   "Configura un servidor web Nginx en WSL que sirva archivos desde C:\\Users\\steve\\www", "Setup nginx"),
        ("Monitorear en tiempo real", "Monitorea el sistema durante 30 segundos y reporta: CPU, RAM, procesos con más consumo y conexiones de red activas.", "Monitor de sistema"),
        ("Instalar herramientas",     "Instala las herramientas de seguridad básicas: nmap, gobuster, python-requests, y cualquier otra que consideres útil.", "Setup de herramientas"),
    ],
}


# ── Diálogo principal ──────────────────────────────────────────────────────

class ReferencesDialog(QDialog):
    insert_to_chat = Signal(str)
    insert_to_terminal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📚 Referencias y Comandos")
        self.setMinimumSize(880, 560)
        self.resize(950, 620)
        self.setWindowFlags(
            Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint
        )
        self._all_items: list[tuple[str, str, str, str]] = []  # cat, title, cmd, desc
        self._build()
        self._populate()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header + search
        header = QWidget()
        header.setObjectName("refs_header")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(16, 12, 16, 12)
        hlay.setSpacing(10)

        title = QLabel("📚 Referencias — Comandos y Snippets")
        title.setObjectName("refs_title")
        hlay.addWidget(title)
        hlay.addStretch()

        self.search = QLineEdit()
        self.search.setObjectName("refs_search")
        self.search.setPlaceholderText("Buscar comandos...")
        self.search.setFixedWidth(260)
        self.search.textChanged.connect(self._filter)
        hlay.addWidget(self.search)

        lay.addWidget(header)

        # Splitter: categories | detail
        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("refs_splitter")

        # Category tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("refs_tabs")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        splitter.addWidget(self.tabs)

        # Right: detail
        right = QWidget()
        right.setMinimumWidth(320)
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(0, 0, 0, 0)
        rlay.setSpacing(0)

        self.detail_title = QLabel("Selecciona un comando")
        self.detail_title.setObjectName("refs_detail_title")
        self.detail_title.setWordWrap(True)
        self.detail_title.setContentsMargins(12, 12, 12, 4)
        rlay.addWidget(self.detail_title)

        self.detail_desc = QLabel("")
        self.detail_desc.setObjectName("refs_detail_desc")
        self.detail_desc.setWordWrap(True)
        self.detail_desc.setContentsMargins(12, 0, 12, 8)
        rlay.addWidget(self.detail_desc)

        self.detail_code = QTextEdit()
        self.detail_code.setObjectName("refs_detail_code")
        self.detail_code.setReadOnly(True)
        font = QFont("Cascadia Code", 11)
        if not font.exactMatch():
            font = QFont("Consolas", 11)
        self.detail_code.setFont(font)
        rlay.addWidget(self.detail_code, 1)

        # Action buttons
        btn_row = QWidget()
        btn_row.setObjectName("refs_btn_row")
        blay = QHBoxLayout(btn_row)
        blay.setContentsMargins(12, 8, 12, 12)
        blay.setSpacing(8)

        self.btn_chat = QPushButton("💬 Enviar al Chat")
        self.btn_chat.setObjectName("refs_btn_chat")
        self.btn_chat.clicked.connect(self._send_chat)

        self.btn_terminal = QPushButton("⚡ Enviar al Terminal")
        self.btn_terminal.setObjectName("refs_btn_terminal")
        self.btn_terminal.clicked.connect(self._send_terminal)

        self.btn_copy = QPushButton("📋 Copiar")
        self.btn_copy.setObjectName("refs_btn_copy")
        self.btn_copy.clicked.connect(self._copy)

        blay.addWidget(self.btn_chat)
        blay.addWidget(self.btn_terminal)
        blay.addStretch()
        blay.addWidget(self.btn_copy)
        rlay.addWidget(btn_row)

        splitter.addWidget(right)
        splitter.setSizes([540, 340])
        lay.addWidget(splitter, 1)

        self._current_cmd = ""

    def _populate(self):
        self._all_items.clear()
        for category, cmds in REFERENCES.items():
            list_widget = QListWidget()
            list_widget.setObjectName("refs_list")
            list_widget.currentItemChanged.connect(self._on_item_selected)

            for title, cmd, desc in cmds:
                item = QListWidgetItem(f"  {title}")
                item.setData(Qt.UserRole, (category, title, cmd, desc))
                list_widget.addItem(item)
                self._all_items.append((category, title, cmd, desc))

            self.tabs.addTab(list_widget, category.split(" — ")[0])

    def _on_tab_changed(self, idx):
        self.detail_title.setText("Selecciona un comando")
        self.detail_desc.setText("")
        self.detail_code.clear()
        self._current_cmd = ""

    def _on_item_selected(self, current, previous):
        if not current:
            return
        data = current.data(Qt.UserRole)
        if not data:
            return
        _, title, cmd, desc = data
        self.detail_title.setText(title)
        self.detail_desc.setText(desc)
        self.detail_code.setPlainText(cmd)
        self._current_cmd = cmd

    def _filter(self, text: str):
        text = text.lower().strip()
        if not text:
            for i in range(self.tabs.count()):
                lw = self.tabs.widget(i)
                for j in range(lw.count()):
                    lw.item(j).setHidden(False)
            return

        for i in range(self.tabs.count()):
            lw = self.tabs.widget(i)
            for j in range(lw.count()):
                item = lw.item(j)
                data = item.data(Qt.UserRole)
                if data:
                    _, title, cmd, desc = data
                    visible = text in title.lower() or text in cmd.lower() or text in desc.lower()
                    item.setHidden(not visible)

    def _send_chat(self):
        if self._current_cmd:
            self.insert_to_chat.emit(self._current_cmd)

    def _send_terminal(self):
        if self._current_cmd:
            self.insert_to_terminal.emit(self._current_cmd)

    def _copy(self):
        if self._current_cmd:
            from PySide6.QtGui import QGuiApplication
            QGuiApplication.clipboard().setText(self._current_cmd)
            self.btn_copy.setText("✓ Copiado")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 Copiar"))
