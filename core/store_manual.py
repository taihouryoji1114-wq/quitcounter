from datetime import datetime
from uuid import uuid4

from core.data import data


class StoreManualManager:
    def __init__(self, data_manager=None):
        self._data_manager = data_manager or data

    def categories(self):
        values = self._data_manager.data.get("store_manual_categories", [])
        return [dict(value) for value in values
                if isinstance(value, dict) and value.get("active", True)]

    def add_category(self, name, color="#E8F2EC", icon="menu_book"):
        name = str(name or "").strip()[:30]
        if not name:
            raise ValueError("カテゴリー名を入力してください。")
        if any(value["name"] == name for value in self.categories()):
            raise ValueError("同じカテゴリーがあります。")
        item = {"id": uuid4().hex, "name": name, "color": str(color or "#E8F2EC")[:20],
                "icon": str(icon or "menu_book")[:40], "active": True}
        self._data_manager.data.setdefault("store_manual_categories", []).append(item)
        self._data_manager.save()
        return dict(item)

    def update_category(self, category_id, name, color, icon):
        item = next((value for value in self._data_manager.data.setdefault(
            "store_manual_categories", []) if value.get("id") == category_id), None)
        if not item:
            raise ValueError("カテゴリーが見つかりません。")
        name = str(name or "").strip()[:30]
        if not name:
            raise ValueError("カテゴリー名を入力してください。")
        item.update(name=name, color=str(color or "#E8F2EC")[:20],
                    icon=str(icon or "menu_book")[:40])
        self._data_manager.save()
        return dict(item)

    def move_category(self, category_id, direction):
        values = self._data_manager.data.setdefault("store_manual_categories", [])
        index = next((i for i, value in enumerate(values) if value.get("id") == category_id), None)
        target = index + direction if index is not None else -1
        if index is None or target < 0 or target >= len(values):
            return False
        values[index], values[target] = values[target], values[index]
        self._data_manager.save()
        return True

    def delete_category(self, category_id):
        if any(value.get("category_id") == category_id for value in self.manuals()):
            raise ValueError("マニュアルが入っているカテゴリーは削除できません。")
        item = next((value for value in self._data_manager.data.setdefault(
            "store_manual_categories", []) if value.get("id") == category_id), None)
        if not item:
            raise ValueError("カテゴリーが見つかりません。")
        item["active"] = False
        self._data_manager.save()

    def manuals(self, category_id=None, include_hidden=False):
        values = [dict(value) for value in self._data_manager.data.get("store_manuals", [])
                  if isinstance(value, dict) and value.get("active", True)
                  and (include_hidden or value.get("visible", True))]
        return [value for value in values if not category_id or value.get("category_id") == category_id]

    @staticmethod
    def _steps(value):
        if isinstance(value, str):
            value = value.splitlines()
        return [str(line).strip()[:160] for line in (value or []) if str(line).strip()][:12]

    def add_manual(self, title, category_id, summary="", steps=None, caution="",
                   image_url="", quiz_note="", visible=True):
        title = str(title or "").strip()[:60]
        if not title:
            raise ValueError("マニュアル名を入力してください。")
        if category_id and not any(value["id"] == category_id for value in self.categories()):
            raise ValueError("カテゴリーが見つかりません。")
        now = datetime.now().isoformat(timespec="seconds")
        item = {"id": uuid4().hex, "title": title, "category_id": category_id or "",
                "summary": str(summary or "").strip()[:180], "steps": self._steps(steps),
                "caution": str(caution or "").strip()[:300],
                "image_url": str(image_url or "").strip()[:500],
                "quiz_note": str(quiz_note or "").strip()[:200],
                "visible": bool(visible), "active": True, "created_at": now,
                "updated_at": now}
        self._data_manager.data.setdefault("store_manuals", []).append(item)
        self._data_manager.save()
        return dict(item)

    def update_manual(self, manual_id, **changes):
        item = next((value for value in self._data_manager.data.setdefault("store_manuals", [])
                     if value.get("id") == manual_id and value.get("active", True)), None)
        if not item:
            raise ValueError("マニュアルが見つかりません。")
        title = str(changes.get("title", item.get("title", ""))).strip()[:60]
        if not title:
            raise ValueError("マニュアル名を入力してください。")
        item.update(title=title, category_id=changes.get("category_id", item.get("category_id", "")),
                    summary=str(changes.get("summary", item.get("summary", ""))).strip()[:180],
                    steps=self._steps(changes.get("steps", item.get("steps", []))),
                    caution=str(changes.get("caution", item.get("caution", ""))).strip()[:300],
                    image_url=str(changes.get("image_url", item.get("image_url", ""))).strip()[:500],
                    quiz_note=str(changes.get("quiz_note", item.get("quiz_note", ""))).strip()[:200],
                    visible=bool(changes.get("visible", item.get("visible", True))),
                    updated_at=datetime.now().isoformat(timespec="seconds"))
        self._data_manager.save()
        return dict(item)

    def delete_manual(self, manual_id):
        item = next((value for value in self._data_manager.data.setdefault("store_manuals", [])
                     if value.get("id") == manual_id), None)
        if not item:
            raise ValueError("マニュアルが見つかりません。")
        item["active"] = False
        self._data_manager.save()


store_manual = StoreManualManager()
