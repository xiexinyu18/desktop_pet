"""录入主人声音：录制一段声音供后续模拟主人声线、TTS 与宠物互动。"""
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QMessageBox,
    QWidget,
)

from desktop_pet.auth.models import User
from desktop_pet.voice.record import record_seconds_to_wav
from desktop_pet.voice.store import VoiceProfileStore


# 建议录制时长（秒），供克隆/TTS 使用
RECORD_DURATION_SEC = 15.0


class VoiceRecordDialog(QDialog):
    """录入主人声音：点击开始录制，录满指定秒数后保存。"""

    def __init__(
        self,
        user: User,
        voice_store: Optional[VoiceProfileStore] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._user = user
        self._voice_store = voice_store or VoiceProfileStore()
        self._recorded_path: Optional[Path] = None
        self._recording = False
        self._timer: Optional[QTimer] = None
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setWindowTitle("录入主人声音")
        self.setFixedSize(360, 220)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("录入一段你的声音，后续将用于模拟你的声线与宠物对话。"))
        layout.addWidget(QLabel(f"建议录制约 {int(RECORD_DURATION_SEC)} 秒，请朗读一段话或自由说话。"))

        self._progress = QProgressBar()
        self._progress.setRange(0, int(RECORD_DURATION_SEC))
        self._progress.setValue(0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._btn_record = QPushButton("开始录制")
        self._btn_record.setMinimumHeight(40)
        self._btn_record.clicked.connect(self._on_record)
        layout.addWidget(self._btn_record)

        self._label_status = QLabel("")
        layout.addWidget(self._label_status)

        btn_skip = QPushButton("暂不录入（可稍后在设置中录入）")
        btn_skip.clicked.connect(self.reject)
        layout.addWidget(btn_skip)

    def _on_record(self) -> None:
        if self._recording:
            return
        self._recording = True
        self._btn_record.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._label_status.setText("正在录制…请说话…")

        # 在后台线程录制，避免阻塞 UI；这里用定时器模拟进度，实际录制在子线程
        try:
            from PyQt6.QtCore import QThread

            class RecordThread(QThread):
                def __init__(self, duration: float, user_id: str):
                    super().__init__()
                    self.duration = duration
                    self.user_id = user_id
                    self.result: Optional[Path] = None

                def run(self):
                    self.result = record_seconds_to_wav(self.duration, self.user_id)

            self._thread = RecordThread(RECORD_DURATION_SEC, self._user.id)
            self._thread.finished.connect(self._on_record_finished)
            self._thread.start()

            # 进度条：每秒更新
            self._elapsed = 0.0
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick_progress)
            self._timer.start(200)
        except Exception as e:
            self._label_status.setText(f"录制失败：{e}")
            self._recording = False
            self._btn_record.setEnabled(True)
            self._progress.setVisible(False)

    def _tick_progress(self) -> None:
        self._elapsed += 0.2
        v = min(int(self._elapsed), int(RECORD_DURATION_SEC))
        self._progress.setValue(v)
        if self._elapsed >= RECORD_DURATION_SEC and self._timer:
            self._timer.stop()

    def _on_record_finished(self) -> None:
        if self._timer and self._timer.isActive():
            self._timer.stop()
        self._recording = False
        self._btn_record.setEnabled(True)
        self._progress.setVisible(False)
        self._progress.setValue(int(RECORD_DURATION_SEC))

        result = None
        if getattr(self, "_thread", None) is not None:
            result = getattr(self._thread, "result", None)
        if result and result.exists():
            self._voice_store.set_sample_path(self._user.id, str(result))
            self._recorded_path = result
            self._label_status.setText("录制完成，已保存。")
            QMessageBox.information(self, "完成", "主人声音已录入，后续将用于与宠物对话的语音。")
            self.accept()
        else:
            self._label_status.setText("录制失败，请检查麦克风权限后重试。")
            QMessageBox.warning(self, "录制失败", "未能保存录音，请检查麦克风权限后重试。")
