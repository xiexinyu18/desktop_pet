"""健康提醒服务：喂食、梳毛、猫砂清理。"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import json

from desktop_pet.config import (
    FEED_REMIND_INTERVAL,
    GROOM_REMIND_INTERVAL,
    HEALTH_DATA_DIR,
    LITTER_REMIND_INTERVAL,
    ensure_dirs,
)
from desktop_pet.health.models import HealthReminder, ReminderType


class HealthReminderService:
    """提醒的加载、保存与下次提醒时间计算。"""
    _filename = "reminders.json"

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or HEALTH_DATA_DIR
        ensure_dirs()

    def _path(self) -> Path:
        return self.data_dir / self._filename

    def _default_interval(self, reminder_type: ReminderType) -> int:
        if reminder_type == ReminderType.FEED:
            return FEED_REMIND_INTERVAL
        if reminder_type == ReminderType.GROOM:
            return GROOM_REMIND_INTERVAL
        return LITTER_REMIND_INTERVAL

    def list_for_pet(self, pet_id: str) -> List[HealthReminder]:
        """获取某宠物的所有提醒。"""
        if not self._path().exists():
            return self._create_defaults(pet_id)
        with open(self._path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("reminders", [])
        out = []
        for item in items:
            if item.get("pet_id") != pet_id:
                continue
            r = HealthReminder.model_validate(item)
            if r.next_at is None and r.last_done_at:
                r.next_at = self._compute_next(r.last_done_at, r.interval_minutes)
            out.append(r)
        if not out:
            out = self._create_defaults(pet_id)
            for r in out:
                self.save(r)
        return out

    def _create_defaults(self, pet_id: str) -> List[HealthReminder]:
        now = datetime.now(timezone.utc)
        return [
            HealthReminder(
                pet_id=pet_id,
                reminder_type=ReminderType.FEED,
                interval_minutes=FEED_REMIND_INTERVAL,
                next_at=now + timedelta(minutes=FEED_REMIND_INTERVAL),
                enabled=True,
            ),
            HealthReminder(
                pet_id=pet_id,
                reminder_type=ReminderType.GROOM,
                interval_minutes=GROOM_REMIND_INTERVAL,
                next_at=now + timedelta(minutes=GROOM_REMIND_INTERVAL),
                enabled=True,
            ),
            HealthReminder(
                pet_id=pet_id,
                reminder_type=ReminderType.LITTER,
                interval_minutes=LITTER_REMIND_INTERVAL,
                next_at=now + timedelta(minutes=LITTER_REMIND_INTERVAL),
                enabled=True,
            ),
        ]

    def _compute_next(self, last_done: datetime, interval_minutes: int) -> datetime:
        return last_done + timedelta(minutes=interval_minutes)

    def save(self, reminder: HealthReminder) -> None:
        """保存单条提醒（合并到全局列表）。"""
        ensure_dirs()
        path = self._path()
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"reminders": []}
        reminders = [HealthReminder.model_validate(r) for r in data["reminders"]]
        # 去重：同 pet_id + type 只保留一条
        reminders = [r for r in reminders if not (r.pet_id == reminder.pet_id and r.reminder_type == reminder.reminder_type)]
        reminders.append(reminder)
        data["reminders"] = [r.model_dump(mode="json") for r in reminders]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def mark_done(self, pet_id: str, reminder_type: ReminderType) -> Optional[HealthReminder]:
        """标记某类提醒已完成，并更新下次时间。"""
        for r in self.list_for_pet(pet_id):
            if r.reminder_type != reminder_type:
                continue
            r.last_done_at = datetime.now(timezone.utc)
            r.next_at = self._compute_next(r.last_done_at, r.interval_minutes)
            self.save(r)
            return r
        return None

    def due_reminders(self, pet_id: str) -> List[HealthReminder]:
        """返回当前已到期的提醒。"""
        now = datetime.now(timezone.utc)
        return [r for r in self.list_for_pet(pet_id) if r.enabled and r.next_at and r.next_at <= now]
