"""
Actualizador de CyberAgent.
- Modo fuente (sin sys.frozen): git pull + pip install
- Modo compilado (sys.frozen): GitHub Releases API + descarga zip + aplica con PowerShell
"""
import os, sys, subprocess, tempfile
import httpx
from PySide6.QtCore import QThread, Signal

REPO          = "FlEtsv/cyber-agent"
BRANCH        = "master"
_API_RELEASES = f"https://api.github.com/repos/{REPO}/releases/latest"
_API_COMMITS  = f"https://api.github.com/repos/{REPO}/commits/{BRANCH}"
_PIP          = [sys.executable, "-m", "pip"]
_BASE         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REQ          = os.path.join(_BASE, "requirements.txt")


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def local_version() -> str:
    """Devuelve la versión local: semver si compiled, sha7 si source."""
    if is_frozen():
        vf = os.path.join(os.path.dirname(sys.executable), "version.txt")
    else:
        vf = os.path.join(_BASE, "version.txt")
    try:
        return open(vf, encoding="utf-8").read().strip()
    except Exception:
        return "0.0.0"


def _parse_ver(v: str) -> tuple:
    v = v.lstrip("v").split("-")[0]
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0, 0, 0)


def _git(*args, timeout=10) -> tuple[int, str]:
    try:
        r = subprocess.run(
            ["git"] + list(args), cwd=_BASE,
            capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return -1, str(e)


# ── Check worker ──────────────────────────────────────────────────────────────
class UpdateChecker(QThread):
    update_available = Signal(str, str)   # local_ver, remote_info
    up_to_date       = Signal(str)        # current version
    check_failed     = Signal(str)

    def run(self):
        local = local_version()
        try:
            if is_frozen():
                with httpx.Client(timeout=8) as c:
                    resp = c.get(_API_RELEASES, headers={"Accept": "application/vnd.github.v3+json"})
                    if resp.status_code != 200:
                        self.check_failed.emit(f"GitHub API {resp.status_code}")
                        return
                    data       = resp.json()
                    remote_ver = data.get("tag_name", "0.0.0").lstrip("v")
                    if _parse_ver(remote_ver) > _parse_ver(local):
                        body = data.get("body", "")[:120].replace("\n", " ")
                        self.update_available.emit(local, f"v{remote_ver} — {body}")
                    else:
                        self.up_to_date.emit(local)
            else:
                self._check_source()
        except Exception as e:
            self.check_failed.emit(str(e))

    def _check_source(self):
        """Modo fuente: comparar TOPOLOGÍA, no SHAs sueltos.

        El repo local puede ir por DELANTE de origin (commits sin pushear),
        en cuyo caso un SHA remoto distinto NO significa que haya algo nuevo
        que descargar. Solo hay actualización si origin/BRANCH tiene commits
        que nuestro HEAD no contiene (estamos "behind"). Ante cualquier fallo
        (offline, ref ausente) caemos a "al día" para no molestar en falso.
        """
        code_l, sha = _git("rev-parse", "HEAD")
        local_sha = sha[:7] if code_l == 0 else "unknown"
        # Refresca la ref remota sin tocar el working tree.
        _git("fetch", "origin", BRANCH, timeout=40)
        code_b, behind = _git("rev-list", "--count", f"HEAD..origin/{BRANCH}")
        n = behind.strip()
        if code_b == 0 and n.isdigit() and int(n) > 0:
            code_m, msg = _git("log", "-1", "--format=%h %s", f"origin/{BRANCH}")
            info = msg.strip()[:70] if code_m == 0 else f"origin/{BRANCH}"
            self.update_available.emit(local_sha, f"{info} ({n} commit(s))")
        else:
            self.up_to_date.emit(local_sha)


# ── Apply worker: modo fuente (git pull) ──────────────────────────────────────
class Updater(QThread):
    progress = Signal(str)
    done     = Signal(str)   # new version
    failed   = Signal(str)

    def run(self):
        self.progress.emit("⬇  Descargando cambios de GitHub...")
        code, out = _git("pull", "origin", BRANCH, "--ff-only", timeout=60)
        if code != 0:
            self.failed.emit(out)
            return
        self.progress.emit(out or "Código actualizado.")

        if os.path.isfile(_REQ):
            self.progress.emit("\n📦  Actualizando dependencias...")
            try:
                r = subprocess.run(
                    _PIP + ["install", "-r", _REQ, "--quiet"],
                    capture_output=True, text=True, timeout=180,
                )
                if r.returncode == 0:
                    self.progress.emit("✓ Dependencias OK.")
                else:
                    self.progress.emit(f"⚠ pip: {(r.stdout + r.stderr).strip()}")
            except Exception as e:
                self.progress.emit(f"⚠ pip error: {e}")

        self.progress.emit("\n✓ Actualización completa.")
        code, sha = _git("rev-parse", "HEAD")
        self.done.emit(sha[:7] if code == 0 else local_version())


# ── Apply worker: modo compilado (GitHub Release download) ────────────────────
class ReleaseUpdater(QThread):
    progress = Signal(str)
    ready    = Signal(str)   # zip_path, listo para aplicar
    failed   = Signal(str)

    def run(self):
        try:
            self.progress.emit("🔍  Consultando GitHub Releases...")
            with httpx.Client(timeout=15, follow_redirects=True) as c:
                resp = c.get(_API_RELEASES, headers={"Accept": "application/vnd.github.v3+json"})
                resp.raise_for_status()
                data = resp.json()

            asset = next(
                (a for a in data.get("assets", [])
                 if "CyberAgent-" in a["name"]
                 and "windows" in a["name"].lower()
                 and "Installer" not in a["name"]),
                None,
            )
            if not asset:
                self.failed.emit("No se encontró el asset Windows en el release.")
                return

            url  = asset["browser_download_url"]
            size = asset.get("size", 0)
            self.progress.emit(
                f"⬇  Descargando {asset['name']} ({size // 1024 // 1024} MB)..."
            )

            zip_path   = os.path.join(tempfile.gettempdir(), asset["name"])
            downloaded = 0
            with httpx.Client(timeout=600, follow_redirects=True) as c:
                with c.stream("GET", url) as r:
                    r.raise_for_status()
                    with open(zip_path, "wb") as f:
                        for chunk in r.iter_bytes(chunk_size=524288):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if size:
                                pct = int(downloaded / size * 100)
                                self.progress.emit(
                                    f"  {pct}%  ({downloaded // 1048576} / {size // 1048576} MB)"
                                )

            if size and downloaded != size:
                self.failed.emit(f"Descarga incompleta: {downloaded}/{size} bytes")
                try:
                    os.unlink(zip_path)
                except Exception:
                    pass
                return
            self.progress.emit(f"✓  Descargado: {zip_path}")
            self.ready.emit(zip_path)

        except Exception as e:
            self.failed.emit(str(e))


def apply_frozen_update(zip_path: str) -> None:
    """
    Lanza un script PowerShell desacoplado que aplica la actualización
    después de que la app cierre. Llamar justo antes de QApplication.quit().
    """
    exe_path = sys.executable
    inst_dir = os.path.dirname(exe_path)

    ps = f"""
$zip     = '{zip_path.replace("'", "''")}'
$dst     = '{inst_dir.replace("'", "''")}'
$exe     = '{exe_path.replace("'", "''")}'
$extract = Join-Path $env:TEMP 'cyberagent_update_tmp'

Start-Sleep -Seconds 3

if (Test-Path $extract) {{ Remove-Item $extract -Recurse -Force }}
Expand-Archive -Path $zip -DestinationPath $extract -Force

$src = (Get-ChildItem $extract -Directory | Select-Object -First 1).FullName
if (-not $src) {{ $src = $extract }}

Get-ChildItem $src | ForEach-Object {{
    if ($_.Name -ne 'data') {{
        $target = Join-Path $dst $_.Name
        if ($_.PSIsContainer) {{
            if (Test-Path $target) {{ Remove-Item $target -Recurse -Force }}
            Copy-Item $_.FullName $target -Recurse -Force
        }} else {{
            Copy-Item $_.FullName $target -Force
        }}
    }}
}}

Remove-Item $zip     -Force -ErrorAction SilentlyContinue
Remove-Item $extract -Recurse -Force -ErrorAction SilentlyContinue

Start-Process -FilePath $exe
"""
    script = os.path.join(tempfile.gettempdir(), "cyberagent_apply_update.ps1")
    with open(script, "w", encoding="utf-8") as f:
        f.write(ps)

    subprocess.Popen(
        ["powershell", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", script],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    )


def relaunch_detached(cmd: list[str], cwd: str | None = None) -> None:
    """Relanza la app de forma robusta tras cerrar la actual.

    Lanza un PowerShell desacoplado que ESPERA a que el proceso actual muera
    (libera el mutex de instancia única) y solo entonces arranca la nueva
    instancia. Esto evita la carrera en la que la nueva instancia ve el mutex
    aún tomado, trae al frente la ventana moribunda y se cierra ella misma
    → la app "se cierra pero no se reabre".
    """
    pid = os.getpid()
    exe = cmd[0]
    args = cmd[1:]
    wd = cwd or os.path.dirname(os.path.abspath(sys.argv[0])) or os.getcwd()

    def _q(s: str) -> str:
        return "'" + str(s).replace("'", "''") + "'"

    arglist = ", ".join(_q(a) for a in args)
    start_args = f" -ArgumentList @({arglist})" if args else ""

    ps = f"""
try {{ Wait-Process -Id {pid} -Timeout 20 -ErrorAction SilentlyContinue }} catch {{}}
Start-Sleep -Milliseconds 600
Start-Process -FilePath {_q(exe)}{start_args} -WorkingDirectory {_q(wd)}
"""
    script = os.path.join(tempfile.gettempdir(), "cyberagent_relaunch.ps1")
    with open(script, "w", encoding="utf-8") as f:
        f.write(ps)

    subprocess.Popen(
        ["powershell", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", script],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )


def restart():
    """Reinicia la app (solo modo fuente) — cierra Qt limpiamente antes de relanzar."""
    relaunch_detached([sys.executable] + sys.argv)
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app:
        app.quit()
    else:
        sys.exit(0)
