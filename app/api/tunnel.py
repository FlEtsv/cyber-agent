"""Gestor del túnel Cloudflare (cloudflared)."""
import os, re, shutil, subprocess, threading, time
import httpx

CLOUD_URL = os.environ.get("CYBERAGENT_CLOUD_URL", "")
SECRET    = os.environ.get("CYBERAGENT_CLOUD_SECRET", "")

# URL pública activa del túnel (para servir archivos por enlace al usuario).
_ACTIVE_TUNNEL_URL: str | None = None
_SINGLETON: "TunnelManager | None" = None
_SINGLETON_LOCK = threading.Lock()


def get_public_url() -> str:
    """Devuelve la URL pública vigente (túnel Cloudflare) o un override por env."""
    return (_ACTIVE_TUNNEL_URL or os.environ.get("CYBERAGENT_PUBLIC_URL", "")).rstrip("/")


def ensure_tunnel(wait_secs: float = 0.0, local_port: int = 8765) -> str:
    """
    Garantiza que el túnel esté arrancado y devuelve la URL pública.
    Idempotente: reutiliza el túnel singleton si ya existe.
    Con wait_secs>0 espera (bloqueante) hasta tener URL — útil al servir un
    archivo para devolver ya un enlace público y no uno local.
    """
    global _SINGLETON
    override = os.environ.get("CYBERAGENT_PUBLIC_URL", "").rstrip("/")
    if override:
        return override
    if _ACTIVE_TUNNEL_URL:
        return _ACTIVE_TUNNEL_URL
    with _SINGLETON_LOCK:
        if _ACTIVE_TUNNEL_URL:
            return _ACTIVE_TUNNEL_URL
        if _SINGLETON is None:
            _SINGLETON = TunnelManager(local_port=local_port)
            _SINGLETON.start(wait_secs=wait_secs if wait_secs > 0 else 0.0)
    if wait_secs > 0:
        deadline = time.time() + wait_secs
        while time.time() < deadline and not _ACTIVE_TUNNEL_URL:
            time.sleep(0.25)
    return _ACTIVE_TUNNEL_URL or ""


class TunnelManager:
    def __init__(self, local_port: int = 8765):
        self.local_port  = local_port
        self._url: str | None               = None
        self._proc: subprocess.Popen | None = None

    @property
    def url(self) -> str | None:
        return self._url

    def start(self, wait_secs: float = 20.0) -> str | None:
        t = threading.Thread(target=self._run, daemon=True, name="cloudflared")
        t.start()
        deadline = time.time() + wait_secs
        while time.time() < deadline and self._url is None:
            time.sleep(0.25)
        return self._url

    def stop(self):
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass

    def _run(self):
        cf = self._find_cloudflared()
        if not cf:
            print(
                "[tunnel] cloudflared no encontrado.\n"
                "         Instala con: winget install Cloudflare.cloudflared"
            )
            return
        try:
            self._proc = subprocess.Popen(
                [cf, "tunnel", "--url",
                 f"http://localhost:{self.local_port}", "--no-autoupdate"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                # Sin ventana de consola (antes saltaba al frente cada vez).
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            url_re = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
            try:
                for line in self._proc.stdout:
                    print(f"[tunnel] {line.rstrip()}")
                    m = url_re.search(line)
                    if m and self._url is None:
                        self._url = m.group(0)
                        global _ACTIVE_TUNNEL_URL
                        _ACTIVE_TUNNEL_URL = self._url
                        self._register(self._url)
            finally:
                self._proc.stdout.close()
        except Exception as e:
            print(f"[tunnel] Error: {e}")

    def _register(self, url: str):
        if not CLOUD_URL or not SECRET:
            return
        try:
            httpx.post(
                f"{CLOUD_URL}/register-tunnel",
                json={"url": url},
                headers={"X-Secret": SECRET},
                timeout=5,
            )
            print(f"[tunnel] ✓ Registrado en Cloud Run → {url}")
        except Exception as e:
            print(f"[tunnel] Error al registrar: {e}")

    @staticmethod
    def _find_cloudflared() -> str | None:
        found = shutil.which("cloudflared")
        if found:
            return found
        candidates = [
            r"C:\ProgramData\cloudflared\cloudflared.exe",
            r"C:\Program Files\cloudflared\cloudflared.exe",
            os.path.expanduser(r"~\.cloudflared\cloudflared.exe"),
            os.path.expanduser(
                r"~\AppData\Local\Microsoft\WinGet\Links\cloudflared.exe"
            ),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None
