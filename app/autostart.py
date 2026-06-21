"""Gestiona el arranque automático de CyberAgent al iniciar Windows (registro HKCU)."""
import os, sys

_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_NAME = "CyberAgent"
_BASE     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT   = os.path.join(_BASE, "main.py")


def _cmd() -> str:
    return f'"{sys.executable}" "{_SCRIPT}"'


def is_enabled() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, _REG_NAME)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


def enable():
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, _REG_NAME, 0, winreg.REG_SZ, _cmd())
    winreg.CloseKey(key)


def disable():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, _REG_NAME)
        winreg.CloseKey(key)
    except OSError:
        pass


def toggle() -> bool:
    """Alterna el estado. Devuelve True si ahora está activado."""
    if is_enabled():
        disable()
        return False
    else:
        enable()
        return True
