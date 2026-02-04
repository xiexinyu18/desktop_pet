"""文字转语音（TTS）：MVP 使用系统/引擎默认声线，后续可接入主人声音克隆。"""
from pathlib import Path
from typing import Optional

from desktop_pet.voice.store import VoiceProfileStore


class TTSEngine:
    """TTS 引擎：输入文字，播放语音。优先使用主人声线（若已录入并接入克隆），否则系统默认。"""

    def __init__(self, voice_store: Optional[VoiceProfileStore] = None):
        self._voice_store = voice_store or VoiceProfileStore()
        self._engine = None
        self._init_engine()

    def _init_engine(self) -> None:
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            # 可选：设置语速、音量
            self._engine.setProperty("rate", 150)
            self._engine.setProperty("volume", 1.0)
        except Exception:
            self._engine = None

    def speak(self, text: str, user_id: Optional[str] = None) -> bool:
        """
        将文字转为语音并播放。
        user_id 若提供且该用户已录入声音，后续可在此接入克隆声线；当前 MVP 使用默认声线。
        """
        if not text or not text.strip():
            return False
        if self._engine is None:
            return False
        try:
            # 后续：若 user_id 且 has_voice(user_id)，可调用克隆 TTS；否则用默认
            self._engine.say(text.strip())
            self._engine.runAndWait()
            return True
        except Exception:
            return False

    def stop(self) -> None:
        """停止当前播放。"""
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass
