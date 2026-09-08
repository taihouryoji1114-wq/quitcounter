from core.store_cleaning import StoreCleaningManager


class MemoryData:
    def __init__(self):
        self.data = {}
        self.saved = 0

    def save(self):
        self.saved += 1


def test_cleaning_defaults_and_daily_toggle():
    memory = MemoryData()
    manager = StoreCleaningManager(memory)
    items = manager.items("2026-09-08")
    assert items and not any(item["done"] for item in items)
    assert manager.toggle("2026-09-08", items[0]["id"]) is True
    assert manager.items("2026-09-08")[0]["done"] is True
    assert manager.items("2026-09-09")[0]["done"] is False


def test_cleaning_template_management_keeps_past_record():
    memory = MemoryData()
    manager = StoreCleaningManager(memory)
    manager.templates()
    manager.save_template("入口を拭く", "玄関")
    item = next(value for value in manager.templates() if value["name"] == "入口を拭く")
    manager.toggle("2026-09-08", item["id"])
    manager.save_template("入口と取手を拭く", "玄関", item["id"])
    assert any(value["name"] == "入口と取手を拭く" for value in manager.templates())
    manager.delete_template(item["id"])
    assert item["id"] not in {value["id"] for value in manager.templates()}
    assert memory.data["store_cleaning_records"]["2026-09-08"][item["id"]]["done"]
