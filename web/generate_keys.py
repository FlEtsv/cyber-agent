"""
Ejecuta una vez para generar las claves VAPID:
  py web/generate_keys.py

Copia los valores en las env vars de Cloud Run:
  VAPID_PRIVATE  →  la clave privada (PEM, una línea)
  VAPID_PUBLIC   →  la clave pública (base64url)
"""
from py_vapid import Vapid
import base64

v = Vapid()
v.generate_keys()

private_pem  = v.private_pem().decode().strip()
public_b64   = base64.urlsafe_b64encode(
    v.public_key.public_bytes(
        __import__('cryptography').hazmat.primitives.serialization.Encoding.X962,
        __import__('cryptography').hazmat.primitives.serialization.PublicFormat.UncompressedPoint,
    )
).rstrip(b'=').decode()

print("=" * 60)
print("VAPID_PRIVATE (pon esto en Cloud Run):")
print(private_pem)
print()
print("VAPID_PUBLIC (pon esto en Cloud Run y en el .env del PC):")
print(public_b64)
print("=" * 60)
