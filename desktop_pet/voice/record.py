"""录制主人声音样本（WAV），供后续克隆/TTS 使用。"""
import wave
from pathlib import Path
from typing import Optional

from desktop_pet.config import VOICE_SAMPLES_DIR, ensure_dirs

# 采样率与格式（与常见克隆模型兼容）
SAMPLE_RATE = 22050
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit


def record_seconds_to_wav(
    duration_sec: float,
    user_id: str,
    out_path: Optional[Path] = None,
) -> Optional[Path]:
    """
    录制指定秒数的麦克风声音并保存为 WAV。
    返回保存路径，失败返回 None。
    """
    try:
        import sounddevice as sd
        import numpy as np
    except ImportError:
        return None
    ensure_dirs()
    udir = VOICE_SAMPLES_DIR / user_id
    udir.mkdir(parents=True, exist_ok=True)
    if out_path is None:
        out_path = udir / "main.wav"
    out_path = Path(out_path)
    if out_path.suffix.lower() != ".wav":
        out_path = out_path.with_suffix(".wav")

    samples = int(duration_sec * SAMPLE_RATE)
    try:
        rec = sd.rec(samples, samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="int16")
        sd.wait()
    except Exception:
        return None

    try:
        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(rec.tobytes())
    except Exception:
        return None
    return out_path
