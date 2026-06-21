# -*- mode: python ; coding: utf-8 -*-
# Onefile: un solo .exe sin carpetas ni DLLs separadas
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []

for pkg in ('PySide6',):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

for pkg in ('certifi', 'httpx', 'httpcore', 'anyio', 'sniffio', 'h11', 'idna'):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass

hiddenimports += [
    'subprocess', 'threading', 'shutil', 'winreg', 'ctypes',
    'pathlib', 'zipfile', 'tempfile', 'json',
]

excludes = [
    'torch', 'numpy', 'pandas', 'matplotlib', 'scipy', 'sklearn',
    'chromadb', 'sentence_transformers', 'tkinter', 'PyQt5', 'PyQt6',
    'IPython', 'notebook', 'jupyter',
]

a = Analysis(
    ['installer_gui.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

# ── Onefile: todo dentro del exe ──────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='CyberAgentInstaller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    uac_admin=True,
    icon=None,
)
