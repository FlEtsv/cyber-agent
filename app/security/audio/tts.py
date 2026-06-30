"""
AU-05 + AU-07: TTS local → voz por el altavoz elegido.

Prioridad:
  1. edge-tts (Microsoft Edge Neural, multi-idioma, gratuito) → genera wav temporal
  2. pyttsx3 (offline, voces del sistema)
  3. winsound beep (último recurso)

Multi-idioma configurable (AU-07): voz default español.
"""
from __future__ import annotations

import asyncio
import tempfile
import threading
from pathlib import Path

# Voces configurables por idioma (AU-07)
VOICE_MAP: dict[str, str] = {
    "es": "es-ES-AlvaroNeural",
    "en": "en-US-GuyNeural",
    "fr": "fr-FR-HenriNeural",
    "de": "de-DE-ConradNeural",
    "it": "it-IT-DiegoNeural",
}
_current_lang = "es"
_current_voice: str | None = None  # None = usar VOICE_MAP[_current_lang]


def set_language(lang: str, voice: str | None = None):
    global _current_lang, _current_voice
    _current_lang = lang
    _current_voice = voice


def speak(text: str, lang: str | None = None, block: bool = False) -> bool:
    """
    AU-05: Sintetiza texto y lo reproduce.

    Args:
        text: texto a sintetizar
        lang: idioma (None = usar el configurado)
        block: si True, espera a que termine de reproducirse
    """
    _lang = lang or _current_lang
    voice = _current_voice or VOICE_MAP.get(_lang, VOICE_MAP["es"])

    def _do_speak():
        # Intentar edge-tts (online, neural)
        if _try_edge_tts(text, voice):
            return
        # Fallback pyttsx3 (offline)
        if _try_pyttsx3(text, _lang):
            return
        # Último recurso: beep
        try:
            import winsound
            winsound.Beep(800, 300)
        except Exception:
            pass

    if block:
        _do_speak()
        return True
    else:
        t = threading.Thread(target=_do_speak, daemon=True)
        t.start()
        return True


def _try_edge_tts(text: str, voice: str) -> bool:
    try:
        import edge_tts, asyncio

        async def _gen():
            communicate = edge_tts.Communicate(text, voice)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            await communicate.save(tmp_path)
            return tmp_path

        tmp = asyncio.run(_gen())
        from app.security.audio.player import play_wav
        return play_wav(tmp)
    except Exception:
        return False


def _try_pyttsx3(text: str, lang: str) -> bool:
    try:
        import pyttsx3
        engine = pyttsx3.init()
        # Intentar seleccionar voz en español
        voices = engine.getProperty("voices")
        for v in voices:
            if lang in (v.languages or []) or lang in v.name.lower():
                engine.setProperty("voice", v.id)
                break
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception:
        return False
