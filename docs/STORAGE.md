# STORAGE — Almacenamiento en SD/USB Externo

## Estructura de directorios (StorageLayout)

```
SD_ROOT/
├── models/
│   ├── adapters/      # adapters QLoRA entrenados (.bin)
│   ├── merged/        # modelos fusionados (PEFT merge_and_unload)
│   └── datasets/      # datasets de entrenamiento (.jsonl.gz)
├── videos/            # grabaciones de seguridad (retención 15 días)
├── backups/           # backups comprimidos de las DBs (rotación 7d)
└── exports/           # datasets exportados para RunPod
```

## Y-02: Mover modelos Ollama a SD

Ollama almacena los modelos en `%USERPROFILE%\.ollama\models` por defecto.
Para moverlos a la SD:

### 1. Variable de entorno (recomendado)

```powershell
# En PowerShell (añadir a $PROFILE para persistir)
$env:OLLAMA_MODELS = "D:\ollama_models"   # ajustar ruta según SD

# O como variable de usuario permanente
[System.Environment]::SetEnvironmentVariable(
    "OLLAMA_MODELS", "D:\ollama_models", "User"
)
```

### 2. Mover los modelos existentes

```powershell
# 1. Parar Ollama
Stop-Process -Name "ollama" -Force -ErrorAction SilentlyContinue

# 2. Mover la carpeta de modelos
Move-Item "$env:USERPROFILE\.ollama\models" "D:\ollama_models"

# 3. Crear enlace simbólico (opcional, para compatibilidad)
New-Item -ItemType SymbolicLink `
    -Path "$env:USERPROFILE\.ollama\models" `
    -Target "D:\ollama_models"

# 4. Reiniciar Ollama
& "C:\Users\$env:USERNAME\AppData\Local\Programs\Ollama\ollama app.exe"
```

### 3. Verificar

```powershell
ollama list   # debe mostrar los modelos disponibles
```

### Nota sobre `StorageLayout`

El módulo `app.storage.layout` detecta automáticamente la SD:
- Lee `SD_ROOT` env var primero
- Si no, busca unidades `D:\`, `E:\`, `F:\`, `G:\` con al menos 10 GB libres
- Fallback a `data/` local si no hay SD

Para forzar una ruta concreta:

```powershell
$env:SD_ROOT = "D:\cyberagent_storage"
```

## Retención de videos

Los videos de seguridad tienen retención legal de **15 días**.
El servicio `SecurityScheduleService` del supervisor ejecuta `retention.cleanup()` cada 24h.

Para limpieza manual:

```python
from app.storage.retention import cleanup
from app.storage.layout import layout
result = cleanup(layout.videos, max_days=15)
print(f"Eliminados: {result['deleted']} ({result['freed_bytes'] // 1024**2} MB)")
```

## Backup de DBs

Backup automático cada 12h vía `SecurityScheduleService`.
Backups comprimidos (gzip) con rotación de 7 copias.

Manual:

```python
from app.storage.backup import backup_all
from app.storage.layout import layout
backup_all(data_dir=Path("data"), backups_dir=layout.backups)
```
