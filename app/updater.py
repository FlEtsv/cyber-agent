import subprocess, os, sys
import httpx
from PySide6.QtCore import QThread, Signal

REPO     = "FlEtsv/cyber-agent"
BRANCH   = "master"
API_URL  = f"https://api.github.com/repos/{REPO}/commits/{BRANCH}"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQ_FILE = os.path.join(BASE_DIR, "requirements.txt")

# Pip del venv actual (el mismo intérprete que corre la app)
_PIP = [sys.executable, "-m", "pip"]


def _git(*args, timeout=10) -> tuple[int, str]:
    try:
        r = subprocess.run(
            ["git"] + list(args), cwd=BASE_DIR,
            capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return -1, str(e)


def local_sha() -> str:
    code, out = _git("rev-parse", "HEAD")
    return out[:7] if code == 0 else "unknown"


# ── Check worker ──────────────────────────────────────────────────────────
class UpdateChecker(QThread):
    update_available = Signal(str, str)  # local_sha7, remote_info
    up_to_date       = Signal(str)       # current sha7
    check_failed     = Signal(str)

    def run(self):
        local = local_sha()
        if local == "unknown":
            self.check_failed.emit("git no disponible en PATH")
            return
        try:
            with httpx.Client(timeout=8) as client:
                resp = client.get(
                    API_URL,
                    headers={"Accept": "application/vnd.github.v3+json"},
                )
            if resp.status_code != 200:
                self.check_failed.emit(f"GitHub API {resp.status_code}")
                return
            data      = resp.json()
            remote_sha = data["sha"][:7]
            msg        = data["commit"]["message"].split("\n")[0][:60]
            if remote_sha != local:
                self.update_available.emit(local, f"{remote_sha} — {msg}")
            else:
                self.up_to_date.emit(local)
        except Exception as e:
            self.check_failed.emit(str(e))


# ── Apply worker ─────────────────────────────────────────────────────────
class Updater(QThread):
    progress = Signal(str)
    done     = Signal(str)   # new sha7
    failed   = Signal(str)

    def run(self):
        # 1. git pull
        self.progress.emit("⬇  Descargando cambios de GitHub...")
        code, out = _git("pull", "origin", BRANCH, "--ff-only", timeout=60)
        if code != 0:
            self.failed.emit(out)
            return
        self.progress.emit(out or "Código actualizado.")

        # 2. pip install -r requirements.txt (instala nuevas deps de la implementación)
        if os.path.isfile(REQ_FILE):
            self.progress.emit("\n📦  Instalando/actualizando dependencias...")
            try:
                r = subprocess.run(
                    _PIP + ["install", "-r", REQ_FILE, "--quiet"],
                    capture_output=True, text=True, timeout=180,
                )
                if r.returncode == 0:
                    self.progress.emit("✓ Dependencias OK.")
                else:
                    # No es fatal — avisamos pero continuamos
                    self.progress.emit(f"⚠ pip warning:\n{(r.stdout + r.stderr).strip()}")
            except Exception as e:
                self.progress.emit(f"⚠ pip error: {e}")

        self.progress.emit("\n✓ Actualización completa.")
        self.done.emit(local_sha())


# ── Restart helper ────────────────────────────────────────────────────────
def restart():
    import sys, os
    python = sys.executable
    os.execv(python, [python] + sys.argv)
