"""
Blitz Match Guard
-----------------
Blitz te saca del fullscreen al saltar al primer plano dentro de la partida.
Como Blitz solo lo necesitas ANTES de la partida (champ select / builds), este
script lo cierra automáticamente cuando empieza la partida REAL y lo vuelve a
abrir al terminar, para que lo tengas listo para la siguiente.

Detección:
  - Partida en curso  = existe el proceso  League of Legends.exe  (el cliente de
    PARTIDA, distinto de LeagueClientUx.exe que es el lobby/champ select).
  - Al detectar partida -> cierra Blitz (todo su árbol de procesos).
  - Al terminar la partida -> si nosotros lo cerramos, lo reabre.

Sin dependencias externas. Configurable por entorno:
  BLITZ_RELAUNCH=0   -> no reabrir Blitz al terminar la partida.
"""
from __future__ import annotations
import ctypes
import ctypes.wintypes as w
import os
import subprocess
import time

kernel32 = ctypes.windll.kernel32

GAME_PROC = "league of legends.exe"          # proceso de PARTIDA en curso
BLITZ_IMAGE = "Blitz.exe"
BLITZ_PATH = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Blitz", "Blitz.exe")
RELAUNCH = os.environ.get("BLITZ_RELAUNCH", "1") != "0"
POLL = 1.5
LOG = os.path.join(os.environ.get("TEMP", "."), "blitz_match_guard.log")
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008

TH32CS_SNAPPROCESS = 0x00000002


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)), ("th32ModuleID", w.DWORD),
        ("cntThreads", w.DWORD), ("th32ParentProcessID", w.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", w.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def _log(msg: str) -> None:
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except Exception:
        pass


def running_procs() -> set[str]:
    names: set[str] = set()
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    try:
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(pe))
        while ok:
            names.add(pe.szExeFile.lower())
            ok = kernel32.Process32NextW(snap, ctypes.byref(pe))
    except Exception:
        pass
    finally:
        kernel32.CloseHandle(snap)
    return names


def kill_blitz() -> None:
    subprocess.run(["taskkill", "/F", "/T", "/IM", BLITZ_IMAGE],
                   creationflags=CREATE_NO_WINDOW, capture_output=True)


def launch_blitz() -> bool:
    if not os.path.isfile(BLITZ_PATH):
        _log(f"No encuentro Blitz en {BLITZ_PATH}; no lo reabro")
        return False
    try:
        subprocess.Popen([BLITZ_PATH], creationflags=DETACHED_PROCESS, close_fds=True)
        return True
    except Exception as e:
        _log(f"Error reabriendo Blitz: {e}")
        return False


def main() -> None:
    _log(f"blitz_match_guard iniciado (relaunch={'on' if RELAUNCH else 'off'})")
    we_closed = False
    prev_in_game = False
    while True:
        try:
            procs = running_procs()
            in_game = GAME_PROC in procs
            blitz_up = BLITZ_IMAGE.lower() in procs

            if in_game and blitz_up:
                kill_blitz()
                we_closed = True
                _log("Partida detectada -> Blitz cerrado (te dejo el fullscreen en paz)")

            if (not in_game) and prev_in_game and we_closed:
                # acaba de terminar la partida
                if RELAUNCH and BLITZ_IMAGE.lower() not in procs:
                    if launch_blitz():
                        _log("Partida terminada -> Blitz reabierto para el próximo champ select")
                we_closed = False

            prev_in_game = in_game
        except Exception:
            pass
        time.sleep(POLL)


if __name__ == "__main__":
    main()
