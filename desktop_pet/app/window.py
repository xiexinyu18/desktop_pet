"""桌宠常驻窗口：置顶、可拖拽、基础动效。"""
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QApplication, QWidget

from desktop_pet.config import (
    WINDOW_ALWAYS_ON_TOP,
    WINDOW_FRAMELESS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    ensure_dirs,
)
from desktop_pet.app.pet_actor import PetState, next_state_on_detection


class PetWindow(QWidget):
    """桌面宠物窗口：无边框、置顶、可拖拽，根据状态绘制简单动效（MVP 用几何形状代替贴图）。"""

    def __init__(
        self,
        width: int = WINDOW_WIDTH,
        height: int = WINDOW_HEIGHT,
        on_detection: Optional[Callable[[bool], None]] = None,
    ):
        super().__init__()
        self._width = width
        self._height = height
        self._state = PetState.IDLE
        self._drag_pos: Optional[QPoint] = None
        self._on_detection = on_detection
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setWindowTitle("桌宠")
        self.setFixedSize(self._width, self._height)
        if WINDOW_FRAMELESS:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
        else:
            flags = self.windowFlags()
            if WINDOW_ALWAYS_ON_TOP:
                self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

    def set_state(self, state: PetState) -> None:
        self._state = state
        self.update()

    def update_detection(self, pet_detected: bool) -> None:
        """由外部（摄像头检测）调用，更新状态并重绘。"""
        self._state = next_state_on_detection(self._state, pet_detected)
        self.update()
        if self._on_detection:
            self._on_detection(pet_detected)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.set_state(PetState.DRAGGED)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            self.set_state(PetState.IDLE)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        """MVP：用简单图形表示宠物与「眼睛一亮」状态。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 半透明圆作为身体
        body_color = QColor(255, 200, 150, 200)
        painter.setBrush(QBrush(body_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(20, 40, 160, 120)

        # 眼睛
        eye_radius = 12
        if self._state == PetState.EYES_LIT:
            painter.setBrush(QBrush(QColor(255, 255, 100)))
            painter.setPen(QPen(QColor(255, 200, 0), 2))
        else:
            painter.setBrush(QBrush(QColor(60, 60, 80)))
            painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(70, 70, eye_radius * 2, eye_radius * 2)
        painter.drawEllipse(120, 70, eye_radius * 2, eye_radius * 2)

        # 状态文字（调试用，可后续去掉）
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.drawText(10, self._height - 8, self._state.value)

        painter.end()
