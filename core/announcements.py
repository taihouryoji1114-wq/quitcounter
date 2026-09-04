from datetime import datetime
from uuid import uuid4
from core.data import data


class AnnouncementManager:
    def __init__(self, manager=None):
        self.manager = manager or data

    def items(self):
        return [dict(row) for row in self.manager.data.get("store_announcements", [])]

    def save(self, time, message, enabled=True, item_id=None):
        if datetime.strptime(str(time), "%H:%M").strftime("%H:%M") != time:
            raise ValueError("時刻を時:分で入力してください。")
        message = str(message or "").strip()
        if not message or len(message) > 120:
            raise ValueError("セリフは1〜120文字で入力してください。")
        rows = self.manager.data.setdefault("store_announcements", [])
        if not item_id and len(rows) >= 20:
            raise ValueError("アナウンスは20件まで登録できます。")
        item = {"id": item_id or uuid4().hex, "time": time, "message": message, "enabled": bool(enabled)}
        if item_id:
            for index, row in enumerate(rows):
                if row["id"] == item_id:
                    rows[index] = item
                    break
            else:
                raise ValueError("アナウンスが見つかりません。")
        else:
            rows.append(item)
        self.manager.save()
        return item

    def delete(self, item_id):
        rows = self.manager.data.setdefault("store_announcements", [])
        rows[:] = [row for row in rows if row["id"] != item_id]
        self.manager.save()


announcements = AnnouncementManager()
