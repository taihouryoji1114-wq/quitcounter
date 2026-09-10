"""Store fire-safety learning completion records."""
from datetime import datetime
from core.data import data

COURSE_URL = "https://www.tfd.metro.tokyo.lg.jp/learning/contents/jiei/index.html"
COURSE_TITLE = "自衛消防活動要領【電子学習室】"

class FireTrainingManager:
    def __init__(self, data_manager=None): self._data_manager=data_manager or data
    def completions(self):
        values=self._data_manager.data.get("store_fire_training",{}).get("completions",{})
        return {str(k):dict(v) for k,v in values.items() if isinstance(v,dict)}
    def complete(self,staff_name):
        name=str(staff_name or "").strip()
        if not name: raise ValueError("スタッフ名を選んでください。")
        now=datetime.now().astimezone()
        record={"staff_name":name[:40],"completed_at":now.isoformat(timespec="minutes"),"course_url":COURSE_URL,"course_title":COURSE_TITLE}
        self._data_manager.data.setdefault("store_fire_training",{}).setdefault("completions",{})[name]=record
        self._data_manager.save();return record
    def remove(self,staff_name):
        self._data_manager.data.setdefault("store_fire_training",{}).setdefault("completions",{}).pop(str(staff_name),None);self._data_manager.save()

fire_training=FireTrainingManager()
