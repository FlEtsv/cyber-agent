"""
Detección de "app a pantalla completa" (juego) en primer plano.

Sirve para que CyberAgent NO robe el foco ni lance globos de notificación
mientras juegas a pantalla completa (p. ej. League of Legends), que es lo que
te sacaba del juego. Solo Windows; en otros SO devuelve False.
"""
from __future__ import annotations

import sys


def foreground_is_fullscreen() -> bool:
    """True si la ventana en primer plano cubre por completo su monitor."""
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        # El escritorio / shell no cuentan como "juego a pantalla completa".
        if hwnd in (user32.GetShellWindow(), user32.GetDesktopWindow()):
            return False

        wr = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(wr)):
            return False

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        MONITOR_DEFAULTTONEAREST = 2
        hmon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            return False

        m = mi.rcMonitor
        return (
            wr.left <= m.left and wr.top <= m.top
            and wr.right >= m.right and wr.bottom >= m.bottom
        )
    except Exception:
        return False
