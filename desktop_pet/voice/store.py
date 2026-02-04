"""主人声音样本路径存储（按用户 ID）。"""
import json
from pathlib import Path
from typing import Optional

from desktop_pet.config import VOICE_SAMPLES_DIR, ensure_dirs


class VoiceProfileStore:
    """按用户保存主人声音样本路径，供 TTS/克隆使用。"""
    _index_file = "index.json"

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or VOICE_SAMPLES_DIR
        ensure_dirs()

    def _index_path(self) -> Path:
        return self.base_dir / self._index_file

    def _user_dir(self, user_id: str) -> Path:
        return self.base_dir / user_id

    def get_sample_path(self, user_id: str) -> Optional[str]:
        """获取该用户已录入的声音样本路径（主文件）。"""
        udir = self._user_dir(user_id)
        # 约定：用户目录下 main.wav 或第一条 wav
        main = udir / "main.wav"
        if main.exists():
            return str(main)
        for f in udir.glob("*.wav"):
            return str(f)
        return None

    def set_sample_path(self, user_id: str, wav_path: str) -> None:
        """记录用户已录入的声音样本路径。"""
        ensure_dirs()
        udir = self._user_dir(user_id)
        udir.mkdir(parents=True, exist_ok=True)
        dest = udir / "main.wav"
        if wav_path != str(dest):
            import shutil
            shutil.copy2(wav_path, dest)
        index = self._load_index()
        index[user_id] = str(dest)
        self._save_index(index)

    def _load_index(self) -> dict:
        if not self._index_path().exists():
            return {}
        with open(self._index_path(), "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_index(self, data: dict) -> None:
        with open(self._index_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def has_voice(self, user_id: str) -> bool:
        return self.get_sample_path(user_id) is not None
