"""桌宠常驻窗口：置顶、可拖拽、可爱动效（头像/眨眼）；支持内嵌即梦短视频。"""
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal, QUrl
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QMessageBox

from desktop_pet.config import (
    WINDOW_ALWAYS_ON_TOP,
    WINDOW_FRAMELESS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    VIDEOS_DIR,
    JIMENG_ACCESS_KEY,
    JIMENG_SECRET_KEY,
    ensure_dirs,
)
from desktop_pet.app.pet_actor import PetState, next_state_on_detection

# 头像/视频共用：内容区边距，保证图片与视频同一区域、同一比例
CONTENT_MARGIN = 10

# 可选：视频内嵌播放（即梦图生视频）
try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    _HAS_VIDEO = True
except Exception:
    _HAS_VIDEO = False
    QMediaPlayer = None
    QAudioOutput = None
    QVideoWidget = None

# 可选：与宠物说话（TTS）弹窗
try:
    from desktop_pet.voice.tts import TTSEngine
    from desktop_pet.ui.speak_dialog import SpeakDialog
    _HAS_VOICE = True
except Exception:
    _HAS_VOICE = False

# 可选：宠物形象生成（即梦）
try:
    from desktop_pet.ui.avatar_gen_dialog import AvatarGenDialog
    _HAS_AVATAR_GEN = True
except Exception:
    _HAS_AVATAR_GEN = False

# 可选：图生视频 Worker（由窗口持有，避免弹窗关闭时 QThread 被销毁）
try:
    from desktop_pet.jimeng.i2v_worker import I2VWorker
    _HAS_I2V = True
except Exception:
    _HAS_I2V = False
    I2VWorker = None


class PetWindow(QWidget):
    """桌面宠物窗口：无边框、置顶、可拖拽；支持头像图；待机眨眼与轻微弹跳。"""
    returnToWelcomeRequested = pyqtSignal()

    def __init__(
        self,
        width: int = WINDOW_WIDTH,
        height: int = WINDOW_HEIGHT,
        avatar_path: Optional[str] = None,
        on_detection: Optional[Callable[[bool], None]] = None,
        tts_engine: Optional["TTSEngine"] = None,
        user_id: Optional[str] = None,
        pet: Optional[object] = None,
        profile_store: Optional[object] = None,
    ):
        super().__init__()
        self._width = width
        self._height = height
        self._state = PetState.IDLE
        self._drag_pos: Optional[QPoint] = None
        self._on_detection = on_detection
        self._tts_engine = tts_engine
        self._user_id = user_id
        self._pet = pet
        self._profile_store = profile_store
        self._avatar: Optional[QPixmap] = None
        if avatar_path and Path(avatar_path).exists():
            self._avatar = QPixmap(avatar_path)
            if self._avatar.isNull():
                self._avatar = None
        self._eyes_closed = False
        self._last_pet_detected = False  # 用于「人刚出现」时播视频，避免人一直在就反复播导致内存泄漏
        self._video_widget: Optional[QWidget] = None
        self._media_player = None
        self.setup_ui()
        # 若有宠物且已有视频路径，直接内嵌播放；否则启动轮询（i2v 完成后会写入 pet.video_path）
        video_path = getattr(pet, "video_path", None) if pet else None
        if video_path and Path(str(video_path)).exists():
            self._setup_video(str(video_path))
        elif _HAS_VIDEO and pet:
            self._video_poll_timer = QTimer(self)
            self._video_poll_timer.timeout.connect(self._check_pet_video_path)
            self._video_poll_timer.start(2000)
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

        # 与宠物说话（TTS）
        if _HAS_VOICE and self._tts_engine is not None:
            self._btn_speak = QPushButton("说", self)
            self._btn_speak.setFixedSize(26, 22)
            self._btn_speak.setStyleSheet("font-size: 12px; border: 1px solid #ccc; border-radius: 4px; background: rgba(255,255,255,0.9);")
            self._btn_speak.setToolTip("与宠物说话（输入文字转语音）")
            self._btn_speak.setGeometry(self._width - 34, 28, 26, 22)
            self._btn_speak.raise_()
            self._btn_speak.clicked.connect(self._on_speak)

        # 宠物形象生成（即梦 AI 分身）
        if _HAS_AVATAR_GEN and self._pet is not None and self._profile_store is not None:
            self._btn_avatar_gen = QPushButton("形", self)
            self._btn_avatar_gen.setFixedSize(26, 22)
            self._btn_avatar_gen.setStyleSheet("font-size: 12px; border: 1px solid #ccc; border-radius: 4px; background: rgba(255,255,255,0.9);")
            self._btn_avatar_gen.setToolTip("生成 AI 形象（即梦）")
            self._btn_avatar_gen.setGeometry(self._width - 34, 52, 26, 22)
            self._btn_avatar_gen.raise_()
            self._btn_avatar_gen.clicked.connect(self._on_avatar_gen)

    def set_avatar_path(self, path: str) -> None:
        """更新桌宠头像（生成 AI 形象后调用），立即重绘以显示新图。"""
        path = str(path).strip()
        if not path or not Path(path).exists():
            return
        self._avatar = QPixmap(path)
        if self._avatar.isNull():
            self._avatar = None
        self._update_video_widget_geometry()
        self.update()
        self.repaint()

    def set_video_path(self, path: str) -> None:
        """设置并播放即梦短视频（图生视频完成后由弹窗或轮询调用）。"""
        path = str(path).strip()
        if not path or not Path(path).exists():
            return
        if getattr(self, "_pet", None):
            self._pet.video_path = path
            if self._profile_store:
                self._profile_store.save(self._pet)
        # 已有视频控件时只更新源与尺寸（已注册用户重新生成视频后能播新文件）
        if self._video_widget is not None and self._media_player is not None:
            self._media_player.setSource(QUrl.fromLocalFile(path))
            self._update_video_widget_geometry()
            self._media_player.pause()
            self._video_widget.hide()
            self.update()
            return
        self._setup_video(path)

    def _update_video_widget_geometry(self) -> None:
        """按头像图片实际显示尺寸与位置设置视频区域（与 paintEvent 中 scaled 一致）。"""
        if self._video_widget is None:
            return
        content_w = self._width - 2 * CONTENT_MARGIN
        content_h = self._height - 2 * CONTENT_MARGIN
        if self._avatar and not self._avatar.isNull():
            scaled = self._avatar.scaled(
                content_w, content_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            vw, vh = scaled.width(), scaled.height()
            vx = (self._width - vw) // 2
            vy = (self._height - vh) // 2
        else:
            vx, vy = CONTENT_MARGIN, CONTENT_MARGIN
            vw, vh = content_w, content_h
        self._video_widget.setGeometry(vx, vy, vw, vh)

    def _check_pet_video_path(self) -> None:
        """轮询宠物档案中的 video_path（内存 + 磁盘），若新写入则内嵌播放并停止轮询。"""
        if not self._pet or not _HAS_VIDEO or self._video_widget is not None:
            return
        path = getattr(self._pet, "video_path", None)
        # 内存无 path 时从档案重新加载，确保生成后的视频与当前账号绑定
        if not path and self._profile_store:
            try:
                fresh = self._profile_store.load(self._pet.id)
                if fresh:
                    path = getattr(fresh, "video_path", None)
                    if path:
                        self._pet.video_path = path
            except Exception:
                pass
        if path and Path(str(path)).exists():
            if getattr(self, "_video_poll_timer", None):
                self._video_poll_timer.stop()
            self._setup_video(str(path))

    def _setup_video(self, path: str) -> None:
        """内嵌即梦短视频：QVideoWidget + QMediaPlayer，循环、静音，置于按钮下层。"""
        if not _HAS_VIDEO or QVideoWidget is None or QMediaPlayer is None:
            return
        path = str(path)
        if not Path(path).exists():
            return
        if self._video_widget is not None:
            return
        self._video_widget = QVideoWidget(self)
        self._update_video_widget_geometry()
        self._video_widget.setStyleSheet("background: transparent;")
        self._media_player = QMediaPlayer()
        self._media_player.setVideoOutput(self._video_widget)
        # Qt6：音量由 QAudioOutput 控制，静音则设 volume 为 0
        if QAudioOutput is not None:
            self._audio_output = QAudioOutput(self)
            self._audio_output.setVolume(0.0)
            self._media_player.setAudioOutput(self._audio_output)
        self._media_player.setSource(QUrl.fromLocalFile(path))
        # 填满内容区，去除上下黑边（等比放大裁剪，与头像同区域）
        try:
            self._video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        except Exception:
            pass
        # 播完后切回静态图，不循环（检测到人时只播完一遍）
        try:
            from PyQt6.QtMultimedia import QMediaPlayer as QMP
            if hasattr(QMP, "mediaStatusChanged"):
                self._media_player.mediaStatusChanged.connect(self._on_video_media_status)
        except Exception:
            pass
        self._video_widget.lower()
        # 默认不显示视频：等检测到人时再显示并播放（见 update_detection）
        self._video_widget.hide()
        self._media_player.pause()
        self.update()

    def _on_video_media_status(self, status) -> None:
        """视频播完后切回静态图，不中断播放。"""
        try:
            from PyQt6.QtMultimedia import QMediaPlayer as QMP
            if status == QMP.MediaStatus.EndOfMedia and self._media_player and self._video_widget:
                self._media_player.pause()
                self._video_widget.hide()
                self.update()
        except Exception:
            pass

    def _on_avatar_gen(self) -> None:
        if _HAS_AVATAR_GEN and self._pet is not None and self._profile_store is not None:
            dlg = AvatarGenDialog(self._pet, self._profile_store, self)
            # 用 DirectConnection 保证关闭弹窗前就更新头像并重绘，桌宠立即显示新图
            dlg.avatarUpdated.connect(
                self.set_avatar_path,
                Qt.ConnectionType.DirectConnection,
            )
            # 图生视频由窗口持有 Worker，避免弹窗关闭后 QThread 被销毁导致崩溃
            dlg.startI2vRequested.connect(self._on_start_i2v)
            dlg.exec()

    def _on_start_i2v(self, avatar_path: str) -> None:
        """由形象弹窗发出；在窗口内创建并持有 I2VWorker，避免弹窗关闭后线程被销毁。"""
        if not _HAS_I2V or I2VWorker is None or not JIMENG_ACCESS_KEY or not JIMENG_SECRET_KEY:
            return
        ensure_dirs()
        worker = I2VWorker(avatar_path, JIMENG_ACCESS_KEY, JIMENG_SECRET_KEY, VIDEOS_DIR, parent=self)
        worker.finished_success.connect(self._on_i2v_success)
        worker.finished_fail.connect(self._on_i2v_fail)
        worker.start()

    def _on_i2v_success(self, video_path: str) -> None:
        if self._pet and self._profile_store:
            self._pet.video_path = video_path
            self._profile_store.save(self._pet)
        self.set_video_path(video_path)
        QMessageBox.information(self, "短视频", f"已保存至：\n{video_path}\n桌宠窗口将自动播放。")

    def _on_i2v_fail(self, err: str) -> None:
        QMessageBox.warning(self, "短视频生成未完成", err)

    def _on_speak(self) -> None:
        if _HAS_VOICE and self._tts_engine is not None:
            dlg = SpeakDialog(self._tts_engine, self._user_id, self)
            dlg.exec()

    def _on_back_to_welcome(self) -> None:
        self.returnToWelcomeRequested.emit()
        self.close()

    def showEvent(self, event) -> None:
        """窗口显示时同步一次档案中的 video_path，确保新生成的视频与当前账号绑定。"""
        super().showEvent(event)
        if self._video_widget is not None or not self._pet or not _HAS_VIDEO:
            return
        path = getattr(self._pet, "video_path", None)
        if not path and self._profile_store:
            try:
                fresh = self._profile_store.load(self._pet.id)
                if fresh:
                    path = getattr(fresh, "video_path", None)
                    if path:
                        self._pet.video_path = path
            except Exception:
                pass
        if path and Path(str(path)).exists():
            self._setup_video(str(path))
            if getattr(self, "_video_poll_timer", None):
                self._video_poll_timer.stop()

    def _start_idle_animations(self) -> None:
        """待机：每隔几秒眨眼（已移除上下弹跳动效）。"""
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._do_blink)
        self._blink_timer.start(3000)

    def _do_blink(self) -> None:
        if self._state != PetState.IDLE and self._state != PetState.EYES_LIT:
            return
        self._eyes_closed = True
        self.update()
        QTimer.singleShot(120, self._open_eyes)

    def _open_eyes(self) -> None:
        self._eyes_closed = False
        self.update()

    def set_state(self, state: PetState) -> None:
        self._state = state
        self.update()

    def update_detection(self, pet_detected: bool) -> None:
        self._state = next_state_on_detection(self._state, pet_detected)
        # 仅在人「刚出现」时触发播放（从未检测到→检测到），避免人一直在就反复播导致内存泄漏
        if self._video_widget is not None and self._media_player is not None:
            if pet_detected and not self._last_pet_detected and not self._video_widget.isVisible():
                self._video_widget.show()
                self._media_player.play()
        self._last_pet_detected = pet_detected
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
        # 若正在播放内嵌短视频，不绘制头像，由 QVideoWidget 展示
        if self._video_widget is not None and self._video_widget.isVisible():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = self._width, self._height
        content_w = w - 2 * CONTENT_MARGIN
        content_h = h - 2 * CONTENT_MARGIN

        if self._avatar and not self._avatar.isNull():
            # 使用用户上传的猫咪形象：与视频同一内容区与比例（KeepAspectRatio）
            scaled = self._avatar.scaled(
                content_w, content_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (w - scaled.width()) // 2
            y = (h - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            if self._state == PetState.EYES_LIT:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(255, 255, 200, 120)))
                painter.drawEllipse(w // 2 - 25, 30, 50, 30)
        else:
            # 默认可爱几何形象：圆身体 + 眼睛（含眨眼与眼睛一亮）
            body_color = QColor(255, 200, 160, 220)
            painter.setBrush(QBrush(body_color))
            painter.setPen(QPen(QColor(255, 180, 140), 1))
            painter.drawEllipse(15, 35, 170, 115)

            eye_radius = 11
            lx, rx = 72, 122
            ey = 72
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
