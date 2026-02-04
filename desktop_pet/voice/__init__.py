"""主人声音录入与文字转语音（TTS），用于与桌宠对话。"""
from desktop_pet.voice.store import VoiceProfileStore
from desktop_pet.voice.tts import TTSEngine

__all__ = ["VoiceProfileStore", "TTSEngine"]
