# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas         = []
binaries      = []
hiddenimports = []

# ── PySide6 completo ──────────────────────────────────────────────────────────
for pkg in ('PySide6',):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

# ── Paquetes de red / misc ────────────────────────────────────────────────────
for pkg in ('markdown', 'psutil', 'httpx', 'Pygments', 'certifi',
            'httpcore', 'anyio', 'sniffio', 'h11', 'idna'):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass

# ── FastAPI / Uvicorn ─────────────────────────────────────────────────────────
for pkg in ('fastapi', 'starlette', 'uvicorn'):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass

# ── qrcode + Pillow ───────────────────────────────────────────────────────────
for pkg in ('qrcode', 'PIL'):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass

# ── Archivos de datos de la app ───────────────────────────────────────────────
import os
datas += [('version.txt', '.')]
if os.path.isfile('cyber_agent.manifest'):
    datas += [('cyber_agent.manifest', '.')]

# ── Módulos de la app ─────────────────────────────────────────────────────────
hiddenimports += [
    # core
    'app', 'app.database', 'app.tools', 'app.ollama_client',
    'app.styles', 'app.autostart', 'app.updater',
    # widgets
    'app.widgets', 'app.widgets.main_window', 'app.widgets.chat_panel',
    'app.widgets.tool_card', 'app.widgets.terminal_panel',
    'app.widgets.references_panel', 'app.widgets.agent_panel',
    'app.widgets.finetune_dialog', 'app.widgets.mobile_dialog',
    'app.widgets.update_dialog',
    # rag
    'app.rag', 'app.rag.knowledge_base', 'app.rag.retriever',
    # consciousness
    'app.consciousness', 'app.consciousness.system_context',
    'app.consciousness.decision_log', 'app.consciousness.threat_detector',
    # api
    'app.api', 'app.api.server', 'app.api.agent_runner',
    'app.api.tunnel', 'app.api.alert_sender', 'app.api.approval_poller',
    # finetune
    'app.finetune', 'app.finetune.collector',
    # uvicorn internals
    'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.loops.asyncio', 'uvicorn.protocols', 'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.lifespan', 'uvicorn.lifespan.off', 'uvicorn.lifespan.on',
    # qrcode
    'qrcode', 'qrcode.image', 'qrcode.image.pil', 'qrcode.constants',
    # stdlib que PyInstaller a veces pierde
    'sqlite3', 'json', 'subprocess', 'threading', 'socket',
    'urllib.request', 'tempfile', 'pathlib', 'platform',
    'shutil', 'datetime', 're', 'os', 'winreg', 'ctypes',
    'zipfile', 'webbrowser',
]

# ── Excluir paquetes pesados no necesarios ────────────────────────────────────
excludes = [
    'chromadb', 'sentence_transformers', 'torch', 'torchvision', 'torchaudio',
    'numpy', 'scipy', 'sklearn', 'pandas', 'matplotlib',
    'IPython', 'notebook', 'jupyter', 'sympy', 'networkx',
    'tensorflow', 'keras', 'transformers', 'tokenizers', 'huggingface_hub',
    'boto3', 'botocore', 'google', 'azure',
    'tk', 'tkinter', 'wx', 'gtk', 'PyQt5', 'PyQt6',
    'test', 'tests', 'unittest',
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
    uac_admin=True,
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
