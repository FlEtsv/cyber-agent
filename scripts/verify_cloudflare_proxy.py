#!/usr/bin/env python3
"""
Script para verificar que Cloudflare Proxy está configurado correctamente
para el relay de CyberAgent.

Este script comprueba:
1. Que el CNAME está configurado correctamente.
2. Que el tráfico pasa por Cloudflare (headers CF-Ray y CF-Connecting-IP).
3. Que el relay responde correctamente.

Uso:
    python scripts/verify_cloudflare_proxy.py --domain relay.cyberagent.cloud
"""

import argparse
import json
import sys
import time
from typing import Optional, Dict, Any

try:
    import requests
    import dns.resolver
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


def print_header(text: str):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_step(step: int, text: str):
    print(f"\n[Paso {step}] {text}")


def print_result(success: bool, message: str):
    symbol = "✅" if success else "❌"
    print(f"  {symbol} {message}")
    return success


def check_dns_cname(domain: str, expected_target: str) -> bool:
    """Verifica si el CNAME está configurado correctamente."""
    print_step(1, f"Verificar CNAME para {domain}")
    
    if not HAS_DEPS:
        print("  ⚠️  Instala 'dnspython' y 'requests' para verificar DNS:")
        print("  pip install dnspython requests")
        return False
    
    try:
        answers = dns.resolver.resolve(domain, "CNAME")
        for rdata in answers:
            if expected_target in str(rdata.target):
                print_result(
                    True,
                    f"CNAME configurado: {domain} → {rdata.target}"
                )
                return True
        print_result(
            False,
            f"CNAME no apunta a {expected_target}. Target actual: {answers[0].target}"
        )
        return False
    except dns.resolver.NoAnswer:
        print_result(
            False,
            f"No hay registro CNAME para {domain}"
        )
        return False
    except dns.resolver.NXDOMAIN:
        print_result(
            False,
            f"El dominio {domain} no existe"
        )
        return False
    except Exception as e:
        print_result(
            False,
            f"Error al resolver DNS: {e}"
        )
        return False


def check_cloudflare_headers(domain: str, protocol: str = "https") -> bool:
    """Verifica si el tráfico pasa por Cloudflare (headers CF-Ray y CF-Connecting-IP)."""
    print_step(2, f"Verificar headers de Cloudflare en {protocol}://{domain}")
    
    if not HAS_DEPS:
        print("  ⚠️  Instala 'requests' para verificar headers:")
        print("  pip install requests")
        return False
    
    url = f"{protocol}://{domain}"
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "CyberAgent/1.0"},
            timeout=10
        )
        headers = response.headers
        
        has_cf_ray = "CF-Ray" in headers
        has_cf_ip = "CF-Connecting-IP" in headers
        
        if has_cf_ray and has_cf_ip:
            print_result(
                True,
                f"Tráfico pasa por Cloudflare (CF-Ray: {headers.get('CF-Ray')}, CF-Connecting-IP: {headers.get('CF-Connecting-IP')})"
            )
            return True
        else:
            missing = []
            if not has_cf_ray:
                missing.append("CF-Ray")
            if not has_cf_ip:
                missing.append("CF-Connecting-IP")
            print_result(
                False,
                f"Headers de Cloudflare no encontrados: {', '.join(missing)}"
            )
            print(f"  Headers recibidos: {dict(headers)}")
            return False
    except requests.exceptions.SSLError:
        print_result(
            False,
            f"Error de certificado SSL en {url}. ¿Cloudflare está configurado correctamente?"
        )
        return False
    except requests.exceptions.ConnectionError:
        print_result(
            False,
            f"No se pudo conectar a {url}. ¿El dominio está accesible?"
        )
        return False
    except Exception as e:
        print_result(
            False,
            f"Error al verificar headers: {e}"
        )
        return False


def check_relay_websocket(domain: str, host_secret: str) -> bool:
    """Verifica que el relay WebSocket responde correctamente."""
    print_step(3, f"Verificar conexión WebSocket al relay")
    
    try:
        import websockets
        import asyncio
    except ImportError:
        print("  ⚠️  Instala 'websockets' para verificar WebSocket:")
        print("  pip install websockets")
        return False
    
    async def test_websocket():
        uri = f"wss://{domain}"
        headers = {"X-Host-Secret": host_secret}
        
        try:
            async with websockets.connect(uri, extra_headers=headers, timeout=10) as ws:
                # Enviar ping
                await ws.send(json.dumps({"type": "ping"}))
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(response)
                
                if data.get("type") == "pong":
                    print_result(
                        True,
                        f"Relay WebSocket responde correctamente: {response}"
                    )
                    return True
                else:
                    print_result(
                        False,
                        f"Respuesta inesperada del relay: {response}"
                    )
                    return False
        except asyncio.TimeoutError:
            print_result(
                False,
                "Timeout al conectar al relay WebSocket"
            )
            return False
        except Exception as e:
            print_result(
                False,
                f"Error al conectar al relay WebSocket: {e}"
            )
            return False
    
    return asyncio.run(test_websocket())


def check_ssl_certificate(domain: str) -> bool:
    """Verifica que el certificado SSL es válido."""
    print_step(4, f"Verificar certificado SSL para {domain}")
    
    if not HAS_DEPS:
        print("  ⚠️  Instala 'requests' para verificar SSL:")
        print("  pip install requests")
        return False
    
    url = f"https://{domain}"
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "CyberAgent/1.0"},
            timeout=10
        )
        cert = response.connection.sock.getpeercert()
        if cert:
            print_result(
                True,
                f"Certificado SSL válido (emite por: {cert.get('issuer', {}).get('commonName', 'Desconocido')})"
            )
            return True
        else:
            print_result(
                False,
                "No se pudo obtener el certificado SSL"
            )
            return False
    except requests.exceptions.SSLError as e:
        print_result(
            False,
            f"Error de certificado SSL: {e}"
        )
        return False
    except Exception as e:
        print_result(
            False,
            f"Error al verificar SSL: {e}"
        )
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Verificar configuración de Cloudflare Proxy para CyberAgent Relay"
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
        "--host-secret",
        type=str,
        default="JWOtZYO8gu0qImor-C1I609VbnKhwQn_0fRlBVL7hdA",
        help="Host secret del relay (para probar WebSocket)",
    )
    args = parser.parse_args()
    
    print_header("VERIFICACIÓN DE CLOUDFLARE PROXY PARA CYBERAGENT RELAY")
    print(f"  Dominio: {args.domain}")
    print(f"  Target:   {args.target}")
    
    results = []
    
    # Paso 1: Verificar CNAME
    results.append(("CNAME", check_dns_cname(args.domain, args.target)))
    
    # Paso 2: Verificar headers de Cloudflare
    results.append(("Cloudflare Headers", check_cloudflare_headers(args.domain)))
    
    # Paso 3: Verificar SSL
    results.append(("SSL Certificate", check_ssl_certificate(args.domain)))
    
    # Paso 4: Verificar WebSocket (opcional, requiere host_secret)
    if args.host_secret:
        results.append(("WebSocket Relay", check_relay_websocket(args.domain, args.host_secret)))
    
    # Resumen
    print_header("RESUMEN")
    all_passed = all(result for _, result in results)
    
    for name, result in results:
        symbol = "✅" if result else "❌"
        print(f"  {symbol} {name}: {'OK' if result else 'FALLÓ'}")
    
    if all_passed:
        print("\n  🎉 ¡Todo está configurado correctamente!")
        print(f"  El relay está accesible en: https://{args.domain}")
    else:
        print("\n  ⚠️  Algunos checks fallaron. Revisa los errores arriba.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
