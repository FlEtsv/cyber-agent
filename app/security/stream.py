"""
N-08: Proxy de stream de cámara (STUB).

Objetivo: recibir RTSP / HA camera_proxy y reemitir como WebRTC / HLS / MJPEG
para que el navegador pueda mostrar el vídeo en tiempo real sin plugins.

Herramienta recomendada: go2rtc (https://github.com/AlexxIT/go2rtc)
  - Corre como sidecar; el server le pasa la URL RTSP de cada cámara.
  - Expone /api/ws?src=<name> (WebRTC) y /api/stream.m3u8 (HLS).
  - La tarjeta de cámara en la web puede usar <video> + Hls.js o RTCPeerConnection.

Estado: PENDIENTE — requiere go2rtc o ffmpeg en el servidor de seguridad.
"""
from __future__ import annotations


def stream_url(cam_id: int, source_url: str, protocol: str = "hls") -> str | None:
    """
    Devuelve la URL del stream convertido para el protocolo solicitado.
    Retorna None si el proxy no está disponible.

    Args:
        cam_id: id de la cámara
        source_url: URL RTSP o entity_id de HA
        protocol: 'hls' | 'webrtc' | 'mjpeg'
    """
    # TODO N-08: integrar con go2rtc o ffmpeg
    return None


def is_available() -> bool:
    """Retorna True si el proxy de stream está configurado y accesible."""
    return False
