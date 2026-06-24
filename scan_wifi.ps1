# Escaneo de dispositivos conectados a la red WiFi
$network = "192.168.18"
$devices = @()

for ($i = 1; $i -le 254; $i++) {
    $ip = "$network.$i"
    
    # Solo verificar IPs activas (con respuesta al ping)
    if (Test-Connection -ComputerName $ip -Count 1 -Quiet) {
        $mac = arp -a | Select-String $ip
        $macAddress = ($mac -split '\s+')[2]
        
        $devices += [PSCustomObject]@{
            IP = $ip
            MAC = $macAddress
            Hostname = (Resolve-DnsName -Name $ip -ErrorAction SilentlyContinue | Select-Object -ExpandProperty NameHost)
        }
    }
}

$devices | Format-Table -AutoSize

# Verificar configuración de WiFi
Write-Host "`nConfiguración actual de la interfaz Wi-Fi:"
netsh wlan show interfaces

# Mostrar redes WiFi disponibles
Write-Host "`nRedes WiFi disponibles:"
netsh wlan show networks