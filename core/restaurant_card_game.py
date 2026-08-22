"""Persistent game rules for the restaurant management card game."""

from __future__ import annotations

import random
from copy import deepcopy
from datetime import datetime


POSITIONS = {"H": "ホール", "D": "デシャップ", "C": "ちゃんこ場", "S": "刺場"}

STAFF_POOL = (
    {"id": "yamada", "name": "山田 健太", "rarity": "SSR", "cost": 5,
     "abilities": {"H": 9, "D": 7, "C": 7, "S": 6}, "skill": "道場魂",
     "effect": "営業時、最も不足している部門を+1支援"},
    {"id": "sakura", "name": "桜井 美咲", "rarity": "SR", "cost": 4,
     "abilities": {"H": 8, "D": 8, "C": 5, "S": 4}, "skill": "笑顔の接客",
     "effect": "ホール配置時、売上+5%"},
    {"id": "ryu", "name": "黒田 龍司", "rarity": "SR", "cost": 4,
     "abilities": {"H": 4, "D": 6, "C": 9, "S": 7}, "skill": "一番出汁",
     "effect": "ちゃんこ場配置時、必要レベル-1"},
    {"id": "ren", "name": "海堂 蓮", "rarity": "R", "cost": 3,
     "abilities": {"H": 5, "D": 5, "C": 6, "S": 8}, "skill": "鮮魚眼",
     "effect": "刺場配置時、サボりポイント+1"},
    {"id": "aoi", "name": "青木 葵", "rarity": "R", "cost": 3,
     "abilities": {"H": 7, "D": 6, "C": 5, "S": 5}, "skill": "気配り",
     "effect": "隣接部門の能力+1"},
    {"id": "tora", "name": "虎谷 一平", "rarity": "SSR", "cost": 5,
     "abilities": {"H": 6, "D": 9, "C": 8, "S": 8}, "skill": "鬼の采配",
     "effect": "全部門達成時、利益+10%"},
    {"id": "momo", "name": "桃井 花", "rarity": "N", "cost": 2,
     "abilities": {"H": 5, "D": 4, "C": 4, "S": 3}, "skill": "新人の情熱",
     "effect": "獲得経験値+20%"},
    {"id": "gen", "name": "源田 誠", "rarity": "N", "cost": 2,
     "abilities": {"H": 3, "D": 4, "C": 5, "S": 5}, "skill": "黙々仕込み",
     "effect": "人件費-1万円"},
)

CUSTOMER_POOL = (
    {"id": "kitsune", "name": "妖狐のコン吉", "rarity": "N", "sales": 180_000,
     "requirements": {"H": 3, "D": 3, "C": 4, "S": 2},
     "image": "/static/rg_customer_kitsune.jpg"},
    {"id": "oni", "name": "ペコペコ鬼", "rarity": "N", "sales": 200_000,
     "requirements": {"H": 3, "D": 3, "C": 4, "S": 2},
     "image": "/static/rg_customer_oni.jpg"},
    {"id": "tanuki", "name": "常連たぬき", "rarity": "N", "sales": 200_000,
     "requirements": {"H": 3, "D": 3, "C": 4, "S": 2},
     "image": "/static/rg_customer_tanuki.jpg"},
    {"id": "tengu", "name": "週末大騒ぎ天狗", "rarity": "R", "sales": 320_000,
     "requirements": {"H": 5, "D": 4, "C": 6, "S": 5},
     "image": "/static/rg_customer_tengu.jpg"},
)


def initial_profile():
    return {
        "year": 1, "cash": 2_000_000, "gems": 500, "support": 0,
        "management_points": 0, "branches": 1, "total_profit": 0,
        "office_level": 0, "manager_id": "", "branch_assets": ["ryogoku"],
        "ceo_level": 1,
        "owned": {"yamada": {"level": 1, "xp": 0, "shards": 0},
                  "momo": {"level": 1, "xp": 0, "shards": 0},
                  "gen": {"level": 1, "xp": 0, "shards": 0}},
        "assignments": {"H": "yamada", "D": "momo", "C": "gen", "S": ""},
        "last_result": None, "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def card(card_id):
    return next((deepcopy(value) for value in STAFF_POOL if value["id"] == card_id), None)


def effective_ability(profile, card_id, position):
    base = card(card_id)
    if not base:
        return 0
    level = int(profile.get("owned", {}).get(card_id, {}).get("level", 1))
    return min(10, int(base["abilities"].get(position, 0)) + (level - 1) // 2)


def run_business(profile, rng=None):
    rng = rng or random.Random()
    year = int(profile.get("year", 1))
    customer = deepcopy(rng.choice(CUSTOMER_POOL))
    requirements = customer["requirements"]
    assignments = profile.get("assignments", {})
    abilities = {key: effective_ability(profile, assignments.get(key, ""), key)
                 for key in POSITIONS}
    if profile.get("manager_id"):
        abilities = {key: min(10, value + 1) for key, value in abilities.items()}
    achieved = {key: abilities[key] >= requirements[key] for key in POSITIONS}
    support = sum(max(0, abilities[key] - requirements[key]) for key in POSITIONS)
    completed = sum(achieved.values())
    sales = sum(customer["sales"] // 4 for key in POSITIONS if achieved[key])
    sales *= max(1, int(profile.get("branches", 1)))
    if assignments.get("H") == "sakura":
        sales = int(sales * 1.05)
    labor = sum(card(value)["cost"] * 10_000 for value in assignments.values() if card(value))
    if "gen" in assignments.values():
        labor = max(0, labor - 10_000)
    rent = 80_000 * profile.get("branches", 1)
    profit = sales - labor - rent
    if completed == 4 and "tora" in assignments.values():
        profit = int(profit * 1.10)
    profile["cash"] = int(profile.get("cash", 0)) + profit
    profile["total_profit"] = int(profile.get("total_profit", 0)) + profit
    profile["support"] = support
    profile["management_points"] = (int(profile.get("management_points", 0)) + completed
                                    + int(profile.get("office_level", 0)))
    for card_id in set(assignments.values()) - {""}:
        owned = profile["owned"].setdefault(card_id, {"level": 1, "xp": 0, "shards": 0})
        owned["xp"] = int(owned.get("xp", 0)) + 15 + completed * 5
    profile["last_result"] = {
        "customer": customer, "requirements": requirements, "abilities": abilities,
        "achieved": achieved,
        "sales": sales, "labor": labor, "rent": rent, "profit": profit,
        "support": support, "completed": completed,
    }
    profile["year"] = year + 1
    profile["gems"] = int(profile.get("gems", 0)) + 30
    profile["updated_at"] = datetime.now().isoformat(timespec="seconds")
    return profile["last_result"]


def promote_manager(profile, card_id):
    if card_id not in profile.get("owned", {}):
        raise ValueError("未獲得のスタッフです。")
    if any(effective_ability(profile, card_id, position) < 5 for position in POSITIONS):
        raise ValueError("店長昇格には全ポジション能力5以上が必要です。")
    profile["manager_id"] = card_id
    return card_id


def open_office(profile):
    if int(profile.get("office_level", 0)):
        raise ValueError("事務所は開設済みです。")
    if int(profile.get("cash", 0)) < 500_000:
        raise ValueError("事務所の開設には50万円必要です。")
    profile["cash"] -= 500_000
    profile["office_level"] = 1
    return 1


def open_branch(profile, branch_id):
    costs = {"nagoya": 700_000, "ginza": 1_500_000}
    if branch_id not in costs:
        raise ValueError("支店が見つかりません。")
    assets = profile.setdefault("branch_assets", ["ryogoku"])
    if branch_id in assets:
        raise ValueError("この支店は開業済みです。")
    if int(profile.get("cash", 0)) < costs[branch_id]:
        raise ValueError("支店を開く資金が足りません。")
    profile["cash"] -= costs[branch_id]
    assets.append(branch_id)
    profile["branches"] = len(assets)
    return len(assets)


def draw_gacha(profile, rng=None):
    rng = rng or random.Random()
    if int(profile.get("gems", 0)) < 100:
        raise ValueError("採用石が足りません。")
    profile["gems"] -= 100
    roll = rng.random()
    rarity = "SSR" if roll < .08 else "SR" if roll < .28 else "R" if roll < .65 else "N"
    candidates = [value for value in STAFF_POOL if value["rarity"] == rarity]
    drawn = deepcopy(rng.choice(candidates))
    if drawn["id"] in profile["owned"]:
        profile["owned"][drawn["id"]]["shards"] += 20
        duplicate = True
    else:
        profile["owned"][drawn["id"]] = {"level": 1, "xp": 0, "shards": 0}
        duplicate = False
    return drawn, duplicate


def level_up(profile, card_id):
    owned = profile.get("owned", {}).get(card_id)
    if not owned:
        raise ValueError("未獲得のスタッフです。")
    level = int(owned.get("level", 1))
    required_xp = level * 40
    if int(owned.get("xp", 0)) < required_xp:
        raise ValueError(f"経験値があと{required_xp - int(owned.get('xp', 0))}必要です。")
    owned["xp"] -= required_xp
    owned["level"] += 1
    return owned["level"]
