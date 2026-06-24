#!/usr/bin/env bash
# ============================================================
# CyberAgent iOS — Build & Deploy to iPhone
# ============================================================
# Requisitos en Mac mini:
#   - Xcode 17+ instalado (xcodebuild disponible en PATH)
#   - Apple Developer account con tu equipo configurado
#   - iPhone conectado por USB y con "Trusted" para este Mac
#   - Xcode tiene tu Bundle ID y firma configurada
#
# Uso:
#   chmod +x ios/build_and_deploy.sh
#   ./ios/build_and_deploy.sh
#
# Variables de entorno opcionales:
#   TEAM_ID         — Tu Apple Developer Team ID (ej: A1B2C3D4E5)
#   BUNDLE_ID       — Bundle identifier (default: com.cyberagent.app)
#   DEVICE_ID       — UDID del iPhone (auto-detectado si hay uno solo)
#   SCHEME          — Nombre del scheme de Xcode (default: CyberAgent)
#   CONFIGURATION   — Debug o Release (default: Debug)
# ============================================================

set -euo pipefail

# ── Config ──────────────────────────────────────────────────
REPO_URL="${REPO_URL:-}"                          # Si se pasa, hace git clone/pull
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"  # Raíz del proyecto
IOS_DIR="${PROJECT_DIR}/ios"
SCHEME="${SCHEME:-CyberAgent}"
CONFIGURATION="${CONFIGURATION:-Debug}"
BUNDLE_ID="${BUNDLE_ID:-com.cyberagent.app}"
TEAM_ID="${TEAM_ID:-}"
BUILD_DIR="${PROJECT_DIR}/build/ios"
APP_NAME="${SCHEME}.app"
IPA_NAME="${SCHEME}.ipa"

# Colores
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── 0. Verificar herramientas ────────────────────────────────
command -v xcodebuild &>/dev/null || error "xcodebuild no encontrado. Instala Xcode 17."
command -v xcrun      &>/dev/null || error "xcrun no encontrado."
info "Xcode version: $(xcodebuild -version | head -1)"

# ── 1. Clonar/actualizar repositorio si se pasa URL ─────────
if [[ -n "${REPO_URL}" ]]; then
    if [[ -d "${PROJECT_DIR}/.git" ]]; then
        info "Actualizando repositorio en ${PROJECT_DIR}..."
        git -C "${PROJECT_DIR}" pull --rebase origin master
    else
        info "Clonando ${REPO_URL}..."
        git clone "${REPO_URL}" "${PROJECT_DIR}"
    fi
fi

# ── 2. Verificar que existen los archivos Swift ──────────────
[[ -f "${IOS_DIR}/Package.swift" ]] || error "Package.swift no encontrado en ${IOS_DIR}"
info "Proyecto iOS encontrado en ${IOS_DIR}"

# ── 3. Detectar iPhone conectado ────────────────────────────
if [[ -z "${DEVICE_ID:-}" ]]; then
    info "Buscando dispositivos iOS conectados..."
    DEVICE_LIST=$(xcrun devicectl list devices 2>/dev/null || xcrun xctrace list devices 2>/dev/null || true)
    # Extraer primer UDID de iPhone/iPad
    DEVICE_ID=$(echo "${DEVICE_LIST}" | grep -E "iPhone|iPad" | grep -v "Simulator" | \
                grep -oE "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}" | head -1 || true)
    if [[ -z "${DEVICE_ID}" ]]; then
        # Intentar con simctl (por si es simulador en dev)
        warn "No se detectó iPhone físico. Intentando en simulador..."
        SIM_ID=$(xcrun simctl list devices available | grep "iPhone" | tail -1 | \
                 grep -oE "[A-F0-9-]{36}" || true)
        DEVICE_ID="${SIM_ID}"
        DESTINATION="platform=iOS Simulator,id=${DEVICE_ID}"
    else
        info "iPhone detectado: ${DEVICE_ID}"
        DESTINATION="platform=iOS,id=${DEVICE_ID}"
    fi
else
    info "Usando DEVICE_ID configurado: ${DEVICE_ID}"
    DESTINATION="platform=iOS,id=${DEVICE_ID}"
fi

[[ -n "${DEVICE_ID}" ]] || error "No se encontró ningún dispositivo iOS. Conecta tu iPhone por USB."

# ── 4. Crear .xcodeproj si no existe (usando xcodegen o SPM) ─
# El proyecto usa Package.swift (SPM), que Xcode puede abrir directamente.
# Para xcodebuild necesitamos un .xcodeproj o trabajar con el Package.swift directamente.

XCODEPROJ="${IOS_DIR}/CyberAgent.xcodeproj"
XCWORKSPACE="${IOS_DIR}/CyberAgent.xcworkspace"

if [[ -f "${XCWORKSPACE}/contents.xcworkspacedata" ]]; then
    BUILD_TARGET="-workspace ${XCWORKSPACE}"
    info "Usando xcworkspace: ${XCWORKSPACE}"
elif [[ -f "${XCODEPROJ}/project.pbxproj" ]]; then
    BUILD_TARGET="-project ${XCODEPROJ}"
    info "Usando xcodeproj: ${XCODEPROJ}"
else
    warn "No se encontró .xcodeproj ni .xcworkspace."
    warn "Necesitas crear el proyecto Xcode primero:"
    warn "  1. Abre Xcode 17"
    warn "  2. File → Open → selecciona ${IOS_DIR}/Package.swift"
    warn "  3. File → Save as Xcode Project → guarda como CyberAgent.xcodeproj en ${IOS_DIR}/"
    warn "  4. Configura: Target → Signing & Capabilities → tu Team ID"
    warn "  5. Vuelve a ejecutar este script"
    error "Proyecto Xcode no configurado."
fi

# ── 5. Build ────────────────────────────────────────────────
mkdir -p "${BUILD_DIR}"
info "Compilando ${SCHEME} (${CONFIGURATION}) para dispositivo ${DEVICE_ID}..."

XCODE_ARGS=(
    ${BUILD_TARGET}
    -scheme "${SCHEME}"
    -configuration "${CONFIGURATION}"
    -destination "${DESTINATION}"
    -derivedDataPath "${BUILD_DIR}/DerivedData"
    CODE_SIGN_STYLE=Automatic
    DEVELOPMENT_TEAM="${TEAM_ID}"
    PRODUCT_BUNDLE_IDENTIFIER="${BUNDLE_ID}"
)

if xcodebuild "${XCODE_ARGS[@]}" build 2>&1 | tee "${BUILD_DIR}/build.log"; then
    info "Build completado correctamente."
else
    error "Build falló. Revisa ${BUILD_DIR}/build.log"
fi

# ── 6. Localizar el .app compilado ───────────────────────────
APP_PATH=$(find "${BUILD_DIR}/DerivedData" -name "${APP_NAME}" -not -path "*/iphoneos/*Simulator*" 2>/dev/null | head -1 || true)
if [[ -z "${APP_PATH}" ]]; then
    APP_PATH=$(find "${BUILD_DIR}/DerivedData" -name "${APP_NAME}" 2>/dev/null | head -1 || true)
fi

[[ -n "${APP_PATH}" ]] || error "No se encontró ${APP_NAME} después del build."
info "App compilada en: ${APP_PATH}"

# ── 7. Instalar en iPhone ────────────────────────────────────
if echo "${DESTINATION}" | grep -q "Simulator"; then
    info "Instalando en simulador ${DEVICE_ID}..."
    xcrun simctl install "${DEVICE_ID}" "${APP_PATH}"
    info "Lanzando en simulador..."
    xcrun simctl launch "${DEVICE_ID}" "${BUNDLE_ID}"
    info "App lanzada en el simulador."
else
    info "Instalando en iPhone ${DEVICE_ID}..."
    # Preferir devicectl (Xcode 15+), fallback a ios-deploy
    if xcrun devicectl device install app --device "${DEVICE_ID}" "${APP_PATH}" 2>/dev/null; then
        info "App instalada con devicectl."
    elif command -v ios-deploy &>/dev/null; then
        ios-deploy --id "${DEVICE_ID}" --bundle "${APP_PATH}" --no-wifi
        info "App instalada con ios-deploy."
    else
        warn "No se pudo instalar automáticamente."
        warn "Opciones manuales:"
        warn "  A) Instala ios-deploy:   brew install ios-deploy"
        warn "     Luego:                ios-deploy --bundle '${APP_PATH}'"
        warn "  B) Arrastra ${APP_NAME} a Xcode → Devices and Simulators (⇧⌘2)"
        warn "  C) Product → Run (⌘R) desde Xcode con el iPhone seleccionado"
    fi
fi

info "✅ Proceso completado."
info "Si la app no aparece en el iPhone, ve a:"
info "  Ajustes → General → VPN y gestión de dispositivos → confiar en tu equipo"
