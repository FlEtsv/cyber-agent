"""Gestor del túnel Cloudflare (cloudflared)."""
import os, re, shutil, subprocess, threading, time
import httpx

CLOUD_URL = os.environ.get("CYBERAGENT_CLOUD_URL", "")
SECRET    = os.environ.get("CYBERAGENT_CLOUD_SECRET", "")


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
            )
            url_re = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
            for line in self._proc.stdout:
                print(f"[tunnel] {line.rstrip()}")
                m = url_re.search(line)
                if m and self._url is None:
                    self._url = m.group(0)
                    self._register(self._url)
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
