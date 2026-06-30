"""
AU-01: Reproductor de audio del PC con selección de dispositivo de salida (Windows).

Usa winsound para WAV, subprocess para mp3 (via Windows Media Player).
Selección de dispositivo: comtypes/pycaw (silencioso) o fallback al defecto del sistema.
"""
from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

_lock = threading.Lock()
_current_device: str | None = None  # None = dispositivo por defecto del sistema


def set_output_device(device_name: str | None):
    """Seleccionar dispositivo de salida de audio."""
    global _current_device
    with _lock:
        _current_device = device_name


def list_devices() -> list[str]:
    """Lista los dispositivos de salida de audio disponibles (Windows)."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-AudioDevice -Playback | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
    except Exception:
        pass
    return ["Dispositivo por defecto"]


def play_wav(path: str | Path) -> bool:
    """Reproduce un WAV usando winsound (bloquea el hilo hasta terminar)."""
    try:
        import winsound
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_NOWAIT)
        return True
    except Exception:
        return _play_via_subprocess(str(path))


def play_async(path: str | Path) -> threading.Thread:
    """Reproduce el archivo en un hilo separado (no bloqueante)."""
    t = threading.Thread(target=play_wav, args=(path,), daemon=True)
    t.start()
    return t


def _play_via_subprocess(path: str) -> bool:
    """Fallback: reproducir via PowerShell Add-Type MediaPlayer."""
    try:
        cmd = (
            f'Add-Type -AssemblyName presentationCore;'
            f'$mp = New-Object system.windows.media.mediaplayer;'
            f'$mp.open([uri]"{path}"); $mp.Play(); Start-Sleep -s 5; $mp.Close()'
        )
        subprocess.Popen(["powershell", "-Command", cmd],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False
