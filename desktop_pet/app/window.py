"""桌宠常驻窗口：置顶、可拖拽、可爱动效（头像/眨眼/弹跳）。"""
import math
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton

from desktop_pet.config import (
    WINDOW_ALWAYS_ON_TOP,
    WINDOW_FRAMELESS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from desktop_pet.app.pet_actor import PetState, next_state_on_detection


class PetWindow(QWidget):
    """桌面宠物窗口：无边框、置顶、可拖拽；支持头像图；待机眨眼与轻微弹跳。"""
    returnToWelcomeRequested = pyqtSignal()

    def __init__(
        self,
        width: int = WINDOW_WIDTH,
        height: int = WINDOW_HEIGHT,
        avatar_path: Optional[str] = None,
        on_detection: Optional[Callable[[bool], None]] = None,
    ):
        super().__init__()
        self._width = width
        self._height = height
        self._state = PetState.IDLE
        self._drag_pos: Optional[QPoint] = None
        self._on_detection = on_detection
        self._avatar: Optional[QPixmap] = None
        if avatar_path and Path(avatar_path).exists():
            self._avatar = QPixmap(avatar_path)
            if self._avatar.isNull():
                self._avatar = None
        self._eyes_closed = False
        self._bounce_offset = 0.0
        self._bounce_phase = 0.0
        self.setup_ui()
        self._start_idle_animations()

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

        # 返回欢迎页按钮（小按钮在右上角）
        self._btn_back = QPushButton("≡", self)
        self._btn_back.setFixedSize(28, 22)
        self._btn_back.setStyleSheet("font-size: 14px; border: 1px solid #ccc; border-radius: 4px; background: rgba(255,255,255,0.9);")
        self._btn_back.setToolTip("返回欢迎页（切换模式）")
        self._btn_back.setGeometry(self._width - 34, 4, 28, 22)
        self._btn_back.raise_()
        self._btn_back.clicked.connect(self._on_back_to_welcome)

    def _on_back_to_welcome(self) -> None:
        self.returnToWelcomeRequested.emit()
        self.close()

    def _start_idle_animations(self) -> None:
        """待机：每隔几秒眨眼；持续轻微弹跳。"""
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._do_blink)
        self._blink_timer.start(3000)

        self._bounce_timer = QTimer(self)
        self._bounce_timer.timeout.connect(self._do_bounce)
        self._bounce_timer.start(80)

    def _do_blink(self) -> None:
        if self._state != PetState.IDLE and self._state != PetState.EYES_LIT:
            return
        self._eyes_closed = True
        self.update()
        QTimer.singleShot(120, self._open_eyes)

    def _open_eyes(self) -> None:
        self._eyes_closed = False
        self.update()

    def _do_bounce(self) -> None:
        if self._state == PetState.DRAGGED:
            return
        self._bounce_phase += 0.25
        self._bounce_offset = 2.0 * math.sin(self._bounce_phase)
        self.update()

    def set_state(self, state: PetState) -> None:
        self._state = state
        self.update()

    def update_detection(self, pet_detected: bool) -> None:
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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        dy = int(self._bounce_offset)
        w, h = self._width, self._height

        if self._avatar and not self._avatar.isNull():
            # 使用用户上传的猫咪形象：缩放绘制，并加「眼睛一亮」高光
            scaled = self._avatar.scaled(
                w - 20, h - 20,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (w - scaled.width()) // 2
            y = (h - scaled.height()) // 2 + dy
            painter.drawPixmap(x, y, scaled)
            if self._state == PetState.EYES_LIT:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(255, 255, 200, 120)))
                painter.drawEllipse(w // 2 - 25, 30 + dy, 50, 30)
        else:
            # 默认可爱几何形象：圆身体 + 眼睛（含眨眼与眼睛一亮）
            body_color = QColor(255, 200, 160, 220)
            painter.setBrush(QBrush(body_color))
            painter.setPen(QPen(QColor(255, 180, 140), 1))
            painter.drawEllipse(15, 35 + dy, 170, 115)

            eye_radius = 11
            lx, rx = 72, 122
            ey = 72 + dy
            if self._eyes_closed:
                painter.setPen(QPen(QColor(80, 60, 40), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawLine(lx - eye_radius, ey, lx + eye_radius, ey)
                painter.drawLine(rx - eye_radius, ey, rx + eye_radius, ey)
            else:
                if self._state == PetState.EYES_LIT:
                    painter.setBrush(QBrush(QColor(255, 255, 150)))
                    painter.setPen(QPen(QColor(255, 220, 80), 2))
                else:
                    painter.setBrush(QBrush(QColor(60, 60, 80)))
                    painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(lx - eye_radius, ey - eye_radius, eye_radius * 2, eye_radius * 2)
                painter.drawEllipse(rx - eye_radius, ey - eye_radius, eye_radius * 2, eye_radius * 2)
                if self._state == PetState.EYES_LIT:
                    painter.setBrush(QBrush(QColor(255, 255, 255)))
                    painter.drawEllipse(lx - 3, ey - 5, 6, 6)
                    painter.drawEllipse(rx - 3, ey - 5, 6, 6)

        painter.end()
