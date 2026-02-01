"""健康提醒测试。"""
import tempfile
from pathlib import Path

from desktop_pet.health.models import HealthReminder, ReminderType
from desktop_pet.health.reminders import HealthReminderService


def test_reminder_service_list_and_save() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        service = HealthReminderService(data_dir=Path(tmp))
        reminders = service.list_for_pet("pet1")
        assert len(reminders) >= 1
        feed = next((r for r in reminders if r.reminder_type == ReminderType.FEED), None)
        assert feed is not None
        assert feed.pet_id == "pet1"
        assert feed.interval_minutes > 0
