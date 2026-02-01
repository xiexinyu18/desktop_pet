"""摄像头宠物检测（运动/轮廓检测，MVP 简化版；后续可接入目标检测模型）。"""
from dataclasses import dataclass
from typing import Optional

from desktop_pet.config import CAMERA_INDEX, CAMERA_DETECT_INTERVAL_MS


@dataclass
class DetectionResult:
    """单次检测结果。"""
    pet_detected: bool
    confidence: float  # 0~1
    message: str = ""


class CameraDetector:
    """摄像头检测：通过运动/轮廓判断是否有「宠物」出现（MVP 用简单运动检测）。"""

    def __init__(
        self,
        camera_index: int = CAMERA_INDEX,
        interval_ms: int = CAMERA_DETECT_INTERVAL_MS,
    ):
        self.camera_index = camera_index
        self.interval_ms = interval_ms
        self._cap = None

    def _ensure_cap(self):
        try:
            import cv2
            if self._cap is None or not self._cap.isOpened():
                self._cap = cv2.VideoCapture(self.camera_index)
            return self._cap is not None and self._cap.isOpened()
        except Exception:
            return False

    def detect(self) -> DetectionResult:
        """执行一次检测。若有明显运动则认为可能有宠物。"""
        if not self._ensure_cap():
            return DetectionResult(
                pet_detected=False,
                confidence=0.0,
                message="摄像头不可用",
            )
        try:
            import cv2
            import numpy as np
            ret, frame = self._cap.read()
            if not ret or frame is None:
                return DetectionResult(False, 0.0, "无法读取画面")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            if not hasattr(self, "_prev_frame") or self._prev_frame is None:
                self._prev_frame = gray
                return DetectionResult(False, 0.0, "初始化")
            diff = cv2.absdiff(self._prev_frame, gray)
            self._prev_frame = gray
            thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
            motion_ratio = float(np.sum(thresh > 0)) / (thresh.shape[0] * thresh.shape[1])
            # 运动面积超过一定比例认为有「活物」
            pet_detected = motion_ratio > 0.02
            confidence = min(1.0, motion_ratio * 10.0)
            return DetectionResult(
                pet_detected=pet_detected,
                confidence=confidence,
                message="运动检测" if pet_detected else "无显著运动",
            )
        except Exception as e:
            return DetectionResult(False, 0.0, str(e))

    def release(self) -> None:
        """释放摄像头。"""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
