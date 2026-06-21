# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []

for pkg in ('PySide6',):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

for pkg in ('certifi', 'httpx'):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass

a = Analysis(
    ['installer_gui.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ['subprocess', 'threading', 'shutil', 'winreg', 'ctypes', 'pathlib'],
    hookspath=[],
    excludes=['torch', 'numpy', 'pandas', 'matplotlib', 'scipy', 'sklearn',
              'chromadb', 'sentence_transformers', 'tkinter', 'PyQt5', 'PyQt6'],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='CyberAgentInstaller',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    uac_admin=True,          # solicita UAC admin automáticamente
    icon=None,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False,
    name='CyberAgentInstaller',
)
