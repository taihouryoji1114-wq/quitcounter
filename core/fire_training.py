"""Store fire-safety learning completion records."""
from datetime import datetime
from core.data import data

COURSE_URL = "https://www.tfd.metro.tokyo.lg.jp/learning/contents/jiei/index.html"
COURSE_TITLE = "自衛消防活動要領【電子学習室】"
STORE_FIELDS = (
    "store_name", "address", "phone", "extinguisher", "emergency_exit",
    "evacuation_route", "fire_door", "fire_equipment", "assembly_point",
)
CHECK_ITEMS = (
    ("extinguisher", "消火器の場所"),
    ("alarm_location", "自動火災報知設備の場所"),
    ("alarm_method", "自動火災報知設備の確認方法"),
    ("hydrant_exists", "屋内消火栓の有無"),
    ("hydrant_location", "屋内消火栓の場所"),
    ("sprinkler_exists", "スプリンクラー設備の有無"),
    ("fire_door", "防火戸の場所"),
    ("fire_shutter", "防火シャッターの場所"),
    ("smoke_control", "排煙設備の場所"),
    ("evacuation_route", "お客様を誘導する避難経路"),
    ("emergency_exit", "非常口"),
    ("evacuation_exit", "避難口"),
)
DEFAULT_ROLE_PLANS = {
    "3": [
        {"role": "119番通報", "detail": "店舗情報と火災状況を通報する"},
        {"role": "初期消火", "detail": "安全を確保できる範囲で消火する"},
        {"role": "避難誘導", "detail": "お客様を安全な出口へ誘導する"},
    ],
    "4": [
        {"role": "119番通報", "detail": "店舗情報と火災状況を通報する"},
        {"role": "初期消火", "detail": "安全を確保できる範囲で消火する"},
        {"role": "避難誘導", "detail": "お客様を安全な出口へ誘導する"},
        {"role": "店内確認", "detail": "逃げ遅れを確認し、無理せず避難する"},
    ],
    "5": [
        {"role": "119番通報", "detail": "店舗情報と火災状況を通報する"},
        {"role": "初期消火", "detail": "安全を確保できる範囲で消火する"},
        {"role": "避難誘導", "detail": "お客様を安全な出口へ誘導する"},
        {"role": "店内確認", "detail": "逃げ遅れを確認し、無理せず避難する"},
        {"role": "消防隊誘導", "detail": "消防隊を案内し、火災・人の情報を伝える"},
    ],
}

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

    def _store(self, store_id="default"):
        key=str(store_id or "default")
        root=self._data_manager.data.setdefault("store_fire_training",{})
        stores=root.setdefault("stores",{})
        return stores.setdefault(key,{"profile":{},"checklist":{},"role_plans":{}})

    def store_settings(self, store_id="default"):
        value=self._store(store_id)
        profile={key:str(value.get("profile",{}).get(key,"")) for key in STORE_FIELDS}
        checklist={key:bool(value.get("checklist",{}).get(key,False)) for key,_ in CHECK_ITEMS}
        plans={key:[dict(item) for item in value.get("role_plans",{}).get(key,DEFAULT_ROLE_PLANS[key])]
               for key in DEFAULT_ROLE_PLANS}
        return {"profile":profile,"checklist":checklist,"role_plans":plans}

    def save_profile(self, values, store_id="default"):
        store=self._store(store_id)
        store["profile"]={key:str((values or {}).get(key,"")).strip()[:300] for key in STORE_FIELDS}
        self._data_manager.save()

    def set_check(self, item_id, checked, store_id="default"):
        valid={key for key,_ in CHECK_ITEMS}
        if item_id not in valid: raise ValueError("確認項目が正しくありません。")
        self._store(store_id).setdefault("checklist",{})[item_id]=bool(checked)
        self._data_manager.save()

    def save_role_plan(self, staff_count, rows, store_id="default"):
        key=str(staff_count)
        if key not in DEFAULT_ROLE_PLANS: raise ValueError("人数設定が正しくありません。")
        cleaned=[]
        for row in rows or []:
            role=str(row.get("role","")).strip()[:50]
            detail=str(row.get("detail","")).strip()[:160]
            if role: cleaned.append({"role":role,"detail":detail})
        if not cleaned: raise ValueError("役割を1つ以上設定してください。")
        self._store(store_id).setdefault("role_plans",{})[key]=cleaned
        self._data_manager.save()

fire_training=FireTrainingManager()
