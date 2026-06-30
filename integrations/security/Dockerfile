# Dockerfile — CyberAgent Security Service
# Imagen Python 3.11 con el backend de seguridad (API + bot Telegram + eventos)
#
# Build: docker build -t cyberagent-sec -f integrations/security/Dockerfile .
# Run:   docker run -p 8766:8766 --env-file integrations/security/.env cyberagent-sec

FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema (ffmpeg para clips de cámara)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Código fuente (solo lo necesario para el módulo de seguridad)
COPY app/ ./app/
COPY apps/ ./apps/
COPY integrations/ ./integrations/

# Crear directorio de datos persistente
RUN mkdir -p /app/data

# Puerto de la API de seguridad
EXPOSE 8766

# Variables de entorno por defecto
ENV SECURITY_ENABLED=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Servidor ASGI con el router de seguridad
CMD ["python", "-m", "uvicorn", "app.api.security_main:app", "--host", "0.0.0.0", "--port", "8766"]
