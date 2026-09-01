"""Persistent rules for the CHANKO life simulation."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime


FOODS = {
    "chanko": {"label": "ちゃんこ", "icon": "🍲", "amount": 34, "speech": "ちゃんこ、もっとちょうだい"},
    "onigiri": {"label": "おにぎり", "icon": "🍙", "amount": 24, "speech": "おにぎり、おいしい"},
    "fish": {"label": "おさかな", "icon": "🐟", "amount": 28, "speech": "おさかな、また食べたい"},
    "snack": {"label": "おやつ", "icon": "🍡", "amount": 16, "speech": "もう一個ほしい"},
}


STAGES = (
    {"level": 1, "name": "ちびっこ期", "threshold": 0},
    {"level": 2, "name": "成長期", "threshold": 6},
    {"level": 3, "name": "成熟期", "threshold": 18},
    {"level": 4, "name": "最終形態", "threshold": 36},
)

ACTIONS = {
    "meal": {"label": "ごはん", "meter": "hunger", "amount": 28, "affection": 2,
             "trait": "food", "speech": "おいしい！ また一緒に食べようね"},
    "play": {"label": "あそぶ", "meter": "joy", "amount": 26, "affection": 2,
             "trait": "play", "speech": "もっと遊びたい！"},
    "bath": {"label": "お風呂", "meter": "cleanliness", "amount": 30, "affection": 1,
             "trait": "bath", "speech": "ぽかぽか。まだ出たくない"},
}


def initial_profile(now=None):
    now = now or datetime.now()
    stamp = now.isoformat(timespec="seconds")
    return {
        "generation": 1,
        "name": "ちゃんこっち",
        "stage": 1,
        "care_points": 0,
        "affection": 0,
        "coins": 30,
        "meters": {"hunger": 72, "cleanliness": 72, "joy": 72},
        "traits": {"food": 0, "play": 0, "bath": 0, "rest": 0, "work": 0},
        "active_dates": [],
        "daily_actions": {},
        "store_reward_dates": [],
        "egg_ready": False,
        "born_at": stamp,
        "history": [],
        "last_speech": "はじめまして。今日から一緒だね！",
        "updated_at": stamp,
        "last_life_tick": stamp,
    }


def normalize_profile(profile, now=None):
    """Fill newly added fields without replacing a player's progress."""
    defaults = initial_profile(now)
    for key, value in defaults.items():
        if key not in profile:
            profile[key] = deepcopy(value)
    for key, value in defaults["meters"].items():
        profile["meters"].setdefault(key, value)
    for key, value in defaults["traits"].items():
        profile["traits"].setdefault(key, value)
    return profile


def stage_info(profile):
    level = max(1, min(4, int(profile.get("stage", 1))))
    return deepcopy(STAGES[level - 1])


def affection_label(value):
    value = int(value or 0)
    if value >= 30:
        return "だいすき"
    if value >= 16:
        return "なかよし"
    if value >= 6:
        return "少し慣れた"
    return "まだ少し緊張"


def next_stage_progress(profile):
    stage = int(profile.get("stage", 1))
    points = int(profile.get("care_points", 0))
    if stage >= 4:
        return 1.0, "最終形態"
    threshold = STAGES[stage]["threshold"]
    previous = STAGES[stage - 1]["threshold"]
    return min(1.0, (points - previous) / max(1, threshold - previous)), f"あと{max(0, threshold - points)}回"


def care(profile, action, business_date, now=None):
    normalize_profile(profile, now)
    if action not in ACTIONS:
        raise ValueError("お世話の種類が正しくありません。")
    rule = ACTIONS[action]
    meters = profile["meters"]
    meters[rule["meter"]] = min(100, int(meters.get(rule["meter"], 0)) + rule["amount"])

    today_actions = profile["daily_actions"].setdefault(business_date, [])
    gained = action not in today_actions
    if gained:
        today_actions.append(action)
        profile["care_points"] = int(profile.get("care_points", 0)) + 1
        profile["affection"] = min(100, int(profile.get("affection", 0)) + rule["affection"])
        profile["traits"][rule["trait"]] = int(profile["traits"].get(rule["trait"], 0)) + 1
        if business_date not in profile["active_dates"]:
            profile["active_dates"].append(business_date)

    evolved = _update_progress(profile)
    profile["last_speech"] = (f"{rule['speech']} 進化したよ！" if evolved else rule["speech"])
    profile["updated_at"] = (now or datetime.now()).isoformat(timespec="seconds")
    return {"gained": gained, "evolved": evolved, "speech": profile["last_speech"]}


def feed(profile, food, business_date, now=None):
    if food not in FOODS:
        raise ValueError("ごはんを選んでください。")
    result = care(profile, "meal", business_date, now)
    profile["meters"]["hunger"] = min(
        100, int(profile["meters"].get("hunger", 0)) - ACTIONS["meal"]["amount"]
        + FOODS[food]["amount"])
    profile["last_food"] = food
    profile["last_speech"] = FOODS[food]["speech"]
    result["speech"] = profile["last_speech"]
    return result


def apply_life_tick(profile, now=None):
    """Let needs change while the app is closed without using background workers."""
    now = now or datetime.now()
    normalize_profile(profile, now)
    try:
        previous = datetime.fromisoformat(profile.get("last_life_tick", ""))
    except ValueError:
        previous = now
    hours = max(0, min(72, int((now - previous).total_seconds() // 3600)))
    if hours:
        profile["meters"]["hunger"] = max(0, int(profile["meters"].get("hunger", 70)) - hours * 3)
        profile["meters"]["joy"] = max(0, int(profile["meters"].get("joy", 70)) - hours * 2)
        profile["meters"]["cleanliness"] = max(0, int(profile["meters"].get("cleanliness", 70)) - hours)
        profile["last_life_tick"] = now.isoformat(timespec="seconds")
    return profile


def current_wish(profile):
    meters = profile.get("meters", {})
    if int(meters.get("hunger", 100)) < 36:
        return "お腹すいた"
    if int(meters.get("joy", 100)) < 36:
        return "あそぼ"
    if int(meters.get("cleanliness", 100)) < 28:
        return "お風呂入りたい"
    return profile.get("last_speech") or "なにする？"


def life_routine(profile, now=None):
    """Choose the creature's current autonomous routine from needs and local time."""
    now = now or datetime.now()
    meters = profile.get("meters", {})
    hunger = int(meters.get("hunger", 70))
    joy = int(meters.get("joy", 70))
    clean = int(meters.get("cleanliness", 70))
    hour = now.hour
    period = ("morning" if 5 <= hour < 11 else "day" if 11 <= hour < 17
              else "evening" if 17 <= hour < 22 else "night")
    if hunger < 36:
        return {"action": "wait_food", "label": "ごはんを待ってる", "period": period}
    if clean < 28:
        return {"action": "want_bath", "label": "お風呂が気になる", "period": period}
    if joy < 36:
        return {"action": "seek_play", "label": "遊び相手を探してる", "period": period}
    if period == "night":
        return {"action": "sleepy", "label": "うとうとしてる", "period": period}
    if period == "morning":
        return {"action": "window", "label": "朝の外を見てる", "period": period}
    return {"action": "wander", "label": "自由に過ごしてる", "period": period}


def claim_store_reward(profile, business_date, now=None):
    normalize_profile(profile, now)
    if business_date in profile["store_reward_dates"]:
        raise ValueError("今日の店舗コインは受け取り済みです。")
    profile["store_reward_dates"].append(business_date)
    profile["coins"] = int(profile.get("coins", 0)) + 10
    profile["traits"]["work"] = int(profile["traits"].get("work", 0)) + 1
    profile["affection"] = min(100, int(profile.get("affection", 0)) + 1)
    profile["last_speech"] = "今日もお仕事おつかれさま！ コインを持って帰ったよ"
    profile["updated_at"] = (now or datetime.now()).isoformat(timespec="seconds")
    return 10


def has_store_activity(source, business_date):
    """Return whether today's shared store checklist contains completed work."""
    records = source.get("store_service_prep_records", {}).get(business_date, {})
    if any(status == "done" for period in records.values() if isinstance(period, dict)
           for status in period.values()):
        return True
    quantities = source.get("store_service_prep_quantities", {}).get(business_date, {})
    if any(int(value or 0) >= 2 for period in quantities.values() if isinstance(period, dict)
           for value in period.values()):
        return True
    choices = source.get("store_service_prep_choices", {}).get(business_date, {})
    if any(value in {"あり", "なし"} for period in choices.values() if isinstance(period, dict)
           for value in period.values()):
        return True
    order_checks = source.get("store_daily_order_checks", {}).get(business_date, {})
    return isinstance(order_checks, dict) and any(bool(value) for value in order_checks.values())


def can_depart(profile):
    return (int(profile.get("stage", 1)) >= 4
            and len(set(profile.get("active_dates", []))) >= 12
            and bool(profile.get("egg_ready")))


def start_next_generation(profile, now=None):
    if not can_depart(profile):
        raise ValueError("まだ次の世代へ進む時ではありません。")
    now = now or datetime.now()
    favorite = max(profile.get("traits", {}), key=profile.get("traits", {}).get,
                   default="play")
    history = list(profile.get("history", []))
    history.append({
        "generation": int(profile.get("generation", 1)),
        "name": profile.get("name", "ちゃんこっち"),
        "stage": stage_info(profile)["name"],
        "affection": int(profile.get("affection", 0)),
        "favorite": favorite,
        "born_at": profile.get("born_at", ""),
        "departed_at": now.isoformat(timespec="seconds"),
    })
    generation = int(profile.get("generation", 1)) + 1
    coins = int(profile.get("coins", 0))
    replacement = initial_profile(now)
    replacement.update({"generation": generation, "coins": coins,
                        "history": history,
                        "last_speech": f"{generation}代目のちゃんタマが生まれたよ！"})
    profile.clear()
    profile.update(replacement)
    return profile


def _update_progress(profile):
    old_stage = int(profile.get("stage", 1))
    points = int(profile.get("care_points", 0))
    new_stage = max(item["level"] for item in STAGES if points >= item["threshold"])
    profile["stage"] = new_stage
    if new_stage >= 3 and len(set(profile.get("active_dates", []))) >= 8:
        profile["egg_ready"] = True
    return new_stage > old_stage
