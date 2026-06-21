# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file para CyberAgent.
Genera dist/CyberAgent/CyberAgent.exe con Python embebido.
"""
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

datas     = []
binaries  = []
hiddenimports = []

# ── Recopilar PySide6 completo ─────────────────────────────────────────────
for pkg in ('PySide6',):
    d, b, h = collect_all(pkg)
    datas        += d
    binaries     += b
    hiddenimports += h

# ── Otros paquetes ─────────────────────────────────────────────────────────
for pkg in ('markdown', 'psutil', 'httpx', 'Pygments', 'certifi', 'httpcore', 'anyio', 'sniffio', 'h11', 'idna'):
    try:
        d, b, h = collect_all(pkg)
        datas        += d
        binaries     += b
        hiddenimports += h
    except Exception:
        pass

# ── Módulos de la app ──────────────────────────────────────────────────────
hiddenimports += [
    'app',
    'app.database',
    'app.tools',
    'app.ollama_client',
    'app.styles',
    'app.widgets',
    'app.widgets.main_window',
    'app.widgets.chat_panel',
    'app.widgets.tool_card',
    'app.widgets.terminal_panel',
    'app.widgets.references_panel',
    'app.rag',
    'app.rag.knowledge_base',
    'app.consciousness',
    'app.consciousness.system_context',
    # stdlib que PyInstaller a veces pierde
    'sqlite3',
    'json',
    'subprocess',
    'threading',
    'socket',
    'urllib.request',
    'tempfile',
    'pathlib',
    'platform',
    'shutil',
    'datetime',
    're',
    'os',
]

# ── Excluir lo que NO necesitamos (reduce tamaño significativamente) ───────
excludes = [
    'chromadb',
    'sentence_transformers',
    'torch',
    'torchvision',
    'torchaudio',
    'numpy',
    'scipy',
    'sklearn',
    'pandas',
    'matplotlib',
    'IPython',
    'notebook',
    'jupyter',
    'sympy',
    'networkx',
    'tensorflow',
    'keras',
    'transformers',
    'tokenizers',
    'huggingface_hub',
    'boto3',
    'botocore',
    'aws',
    'google',
    'azure',
    'tk',
    'tkinter',
    'wx',
    'gtk',
    'PyQt5',
    'PyQt6',
    'test',
    'tests',
    'unittest',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CyberAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=None,
    uac_admin=True,          # solicita permisos de Administrador en Windows
    manifest='cyber_agent.manifest',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='CyberAgent',
)
