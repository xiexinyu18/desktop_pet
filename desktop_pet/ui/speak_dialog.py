"""与宠物说话：输入文字，用主人声线（或默认 TTS）播放，与桌宠互动。"""
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QWidget,
)

from desktop_pet.voice.tts import TTSEngine


class SpeakDialog(QDialog):
    """输入要说的文字，点击播放，用 TTS 朗读（后续可接入主人声线克隆）。"""

    def __init__(
        self,
        tts_engine: TTSEngine,
        user_id: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._tts = tts_engine
        self._user_id = user_id
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setWindowTitle("与宠物说话")
        self.setFixedSize(360, 160)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("输入你想说的话，将用你的声音（或默认语音）播放给宠物听："))
        self._input = QLineEdit()
        self._input.setPlaceholderText("例如：喵喵，过来～")
        layout.addWidget(self._input)

        btn_speak = QPushButton("播放")
        btn_speak.setMinimumHeight(36)
        btn_speak.clicked.connect(self._on_speak)
        layout.addWidget(btn_speak)

    def _on_speak(self) -> None:
        text = self._input.text().strip()
        if not text:
            QMessageBox.information(self, "提示", "请输入要说的内容")
            return
        if self._tts.speak(text, self._user_id):
            pass  # 播放成功，可在此加提示或保持静默
        else:
            QMessageBox.warning(self, "播放失败", "无法播放语音，请检查 TTS 是否可用（如 pyttsx3）。")
