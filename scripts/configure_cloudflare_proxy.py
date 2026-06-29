#!/usr/bin/env python3
"""
Script para configurar Cloudflare como Proxy para Google Cloud Run.

Este script genera las instrucciones y comandos necesarios para:
1. Configurar un CNAME en Cloudflare DNS que apunte a tu Cloud Run.
2. Activar el proxy (nube naranja) en Cloudflare.
3. Verificar que el tráfico pase por Cloudflare.

Uso:
    python scripts/configure_cloudflare_proxy.py --domain relay.cyberagent.cloud --target cyberagent-relay-819820880956.us-central1.run.app
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def print_header(text: str):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_step(step: int, text: str):
    print(f"\n[Paso {step}] {text}")


def print_command(cmd: str, description: str = ""):
    print(f"\n  📌 {description}")
    print(f"  👉 {cmd}")


def verify_dns_propagation(domain: str, target: str, timeout: int = 300):
    """Verifica si el CNAME está propagado (simplificado)."""
    import socket
    import time
    
    print(f"\n  ⏳ Verificando propagación DNS para {domain}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Resolver el CNAME
            cname = socket.gethostbyname_ex(domain)[0]
            if target in cname:
                print(f"  ✅ DNS propagado: {domain} → {cname}")
                return True
        except Exception:
            pass
        time.sleep(10)
    
    print(f"  ⚠️  No se pudo verificar la propagación DNS en {timeout}s.")
    return False


def generate_cloudflare_instructions(domain: str, target: str):
    """Genera instrucciones manuales para configurar Cloudflare."""
    print_header("CONFIGURACIÓN DE CLOUDFLARE PROXY")
    
    print_step(1, f"Configurar CNAME en Cloudflare DNS")
    print(f"""
  1. Ve a https://dash.cloudflare.com/
  2. Selecciona tu dominio (ej: cyberagent.cloud).
  3. Ve a la pestaña "DNS" → "Records".
  4. Haz clic en "Add record" y configura:
     - Type: CNAME
     - Name: {domain.split('.')[0]}  (ej: "relay")
     - Target: {target}
     - Proxy status: 🟠 ON (nube naranja activada)
     - TTL: Auto
  5. Guarda el registro.
""")
    
    print_step(2, "Verificar configuración")
    print(f"""
  1. Espera 5-10 minutos a que se propague el DNS.
  2. Ejecuta este comando para verificar:
     👉 dig {domain} +short
     (Debería devolver: {target})
  3. Verifica que el tráfico pase por Cloudflare:
     👉 curl -v https://{domain}
     (Busca el header "CF-Ray" o "CF-Connecting-IP" en la respuesta).
""")
    
    print_step(3, "Actualizar la aplicación")
    print(f"""
  1. Asegúrate de que tu archivo .env tenga:
     RELAY_URL=https://{domain}
  2. Reinicia CyberAgent para aplicar los cambios.
  3. Verifica los logs de la aplicación:
     Deberías ver: [relay] Conector iniciado → https://{domain}
""")


def generate_curl_test(domain: str):
    """Genera un comando curl para probar la conectividad."""
    print_header("PRUEBA DE CONECTIVIDAD")
    print(f"""
  Ejecuta este comando para probar si el proxy funciona:
  
  👉 curl -v https://{domain}
  
  Busca en la respuesta:
  - Header "CF-Ray": Confirma que el tráfico pasa por Cloudflare.
  - Header "CF-Connecting-IP": IP real del cliente.
  - Código HTTP 200 (si el relay está activo).
  
  Ejemplo de salida esperada:
  < CF-Ray: 8a5b6c7d8e9f0123-MAD
  < CF-Connecting-IP: 203.0.113.195
""")


def main():
    parser = argparse.ArgumentParser(
        description="Configurar Cloudflare Proxy para Google Cloud Run"
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="relay.cyberagent.cloud",
        help="Dominio de Cloudflare (ej: relay.tudominio.com)",
    )
    parser.add_argument(
        "--target",
        type=str,
        default="cyberagent-relay-819820880956.us-central1.run.app",
        help="Target de Cloud Run (ej: tu-app.a.run.app)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Intentar configurar automáticamente (requiere API de Cloudflare)",
    )
    args = parser.parse_args()
    
    print_header("CONFIGURACIÓN DE CLOUDFLARE PROXY PARA GOOGLE CLOUD RUN")
    print(f"  Dominio: {args.domain}")
    print(f"  Target:   {args.target}")
    
    if args.auto:
        print("\n⚠️  La configuración automática requiere:")
        print("  1. API Token de Cloudflare (CF_API_TOKEN)")
        print("  2. Zone ID de tu dominio (CF_ZONE_ID)")
        print("  3. Instalar la librería 'cloudflare' (pip install cloudflare)")
        print("\n  ¿Quieres continuar? (s/n): ", end="")
        response = input().strip().lower()
        if response == "s":
            try:
                import CloudFlare
            except ImportError:
                print("\n  ❌ Instala la librería: pip install cloudflare")
                sys.exit(1)
            
            cf_token = os.environ.get("CF_API_TOKEN")
            cf_zone_id = os.environ.get("CF_ZONE_ID")
            
            if not cf_token or not cf_zone_id:
                print("\n  ❌ Falta CF_API_TOKEN o CF_ZONE_ID en las variables de entorno.")
                sys.exit(1)
            
            # Configurar CNAME via API
            cf = CloudFlare.CloudFlare(token=cf_token)
            zone = cf.zones.get(cf_zone_id)
            
            dns_record = {
                "type": "CNAME",
                "name": args.domain,
                "content": args.target,
                "proxied": True,  # Proxy activado
                "ttl": 1,  # Auto
            }
            
            try:
                response = zone.dns_records.post(data=dns_record)
                print(f"\n  ✅ Registro DNS creado: {response['name']} → {response['content']}")
                print(f"  🔗 ID del registro: {response['id']}")
                print(f"\n  ⏳ Espera 5-10 minutos a que se propague el DNS.")
            except Exception as e:
                print(f"\n  ❌ Error al crear el registro DNS: {e}")
                sys.exit(1)
    else:
        generate_cloudflare_instructions(args.domain, args.target)
    
    generate_curl_test(args.domain)
    
    print_header("RESUMEN")
    print(f"""
  ✅ Configuración lista para:
     - Dominio: {args.domain}
     - Target:  {args.target}
  
  📌 Siguientes pasos:
     1. Configura el CNAME en Cloudflare (manual o automático).
     2. Espera a que se propague el DNS.
     3. Actualiza .env con RELAY_URL=https://{args.domain}
     4. Reinicia CyberAgent.
     5. Verifica con: curl -v https://{args.domain}
""")


if __name__ == "__main__":
    import os
    main()
