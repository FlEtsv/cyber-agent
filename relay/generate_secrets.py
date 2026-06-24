"""
Run this script ONCE to generate the credentials for the Cloud Run relay.
Copy the output into Cloud Run environment variables.

Usage:
    python relay/generate_secrets.py --email tu@correo.com --password tupassword
"""
import sys, secrets, argparse
import bcrypt, pyotp, qrcode

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--email",    required=True)
    p.add_argument("--password", required=True)
    args = p.parse_args()

    pw_hash     = bcrypt.hashpw(args.password.encode(), bcrypt.gensalt()).decode()
    totp_secret = pyotp.random_base32()
    host_secret = secrets.token_urlsafe(32)
    jwt_secret  = secrets.token_hex(32)

    totp = pyotp.TOTP(totp_secret)
    uri  = totp.provisioning_uri(name=args.email, issuer_name="CyberAgent Relay")

    print("\n" + "="*60)
    print("  VARIABLES DE ENTORNO PARA CLOUD RUN")
    print("="*60)
    print(f"RELAY_EMAIL={args.email}")
    print(f"RELAY_PW_HASH={pw_hash}")
    print(f"RELAY_TOTP_SECRET={totp_secret}")
    print(f"HOST_SECRET={host_secret}")
    print(f"JWT_SECRET={jwt_secret}")
    print("="*60)
    print("\nEscanea este QR con Google Authenticator:")
    print(f"URI: {uri}\n")

    qr = qrcode.QRCode()
    qr.add_data(uri)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

    print("\n IMPORTANTE: guarda HOST_SECRET en data/.env del PC:")
    print(f"RELAY_URL=https://TU-RELAY.run.app")
    print(f"RELAY_HOST_SECRET={host_secret}")

if __name__ == "__main__":
    main()
