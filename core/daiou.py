"""Turn based solo nation management rules for 大王."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import random


POLICIES = {
    "prosper": ("富国", "国力と収入を伸ばす", 2, 0, 1),
    "train": ("訓練", "兵を鍛えて抑止力を上げる", 0, 3, 0),
    "guard": ("守備", "城壁と民心を整える", 0, 1, 3),
    "trade": ("交易", "周辺国と争わず資金を得る", 3, 0, 1),
}

NATION_SEEDS = (
    ("暁国", "均衡"), ("北嶺", "守備"), ("蒼海", "交易"), ("紅蓮", "拡大"),
    ("白峰", "富国"), ("翠野", "生存"), ("紫雲", "機会"), ("金砂", "交易"),
    ("黒鉄", "軍備"), ("月影", "外交"),
)


def initial_game(now=None):
    now = now or datetime.now()
    nations = []
    for index, (name, purpose) in enumerate(NATION_SEEDS):
        nations.append({"id": f"n{index}", "name": name, "purpose": purpose,
                        "territory": 1, "wealth": 30, "army": 20,
                        "morale": 70, "walls": 8, "alive": True})
    return {"turn": 1, "season": "春", "player": "n0", "nations": nations,
            "log": ["十の国が並び立つ大陸で、あなたの治世が始まった。"],
            "created_at": now.isoformat(timespec="seconds"),
            "updated_at": now.isoformat(timespec="seconds")}


def normalize_game(game):
    default = initial_game()
    for key, value in default.items():
        game.setdefault(key, deepcopy(value))
    return game


def nation(game, nation_id):
    return next(item for item in game["nations"] if item["id"] == nation_id)


def strength(item):
    """Large countries gain resources but lose cohesion, keeping small states viable."""
    land = max(1, int(item["territory"]))
    cohesion = max(.58, 1.08 - (land - 1) * .055)
    return round((item["army"] * cohesion) + item["walls"] * .65 + item["morale"] * .16)


def apply_policy(game, policy, now=None, seed=None):
    normalize_game(game)
    if policy not in POLICIES:
        raise ValueError("方針を選んでください。")
    player = nation(game, game["player"])
    _, _, wealth, army, morale = POLICIES[policy]
    player["wealth"] += wealth + player["territory"]
    player["army"] += army
    player["morale"] = min(100, player["morale"] + morale)
    if policy == "guard":
        player["walls"] += 2
    rng = random.Random(seed if seed is not None else game["turn"] * 7919)
    messages = [f"{player['name']}は「{POLICIES[policy][0]}」を国策に選んだ。"]
    for cpu in game["nations"]:
        if cpu["id"] == player["id"] or not cpu["alive"]:
            continue
        _cpu_turn(cpu, rng)
    income = max(1, player["territory"] * 3 - max(0, player["territory"] - 3) ** 2)
    player["wealth"] += income
    player["morale"] = max(20, player["morale"] - max(0, player["territory"] - 5))
    messages.append(f"領土収入 {income}。大国ほど統治負担も増える。")
    game["turn"] += 1
    game["season"] = ("春", "夏", "秋", "冬")[(game["turn"] - 1) % 4]
    game["log"] = (messages + game.get("log", []))[:20]
    game["updated_at"] = (now or datetime.now()).isoformat(timespec="seconds")
    return messages


def _cpu_turn(cpu, rng):
    purpose = cpu["purpose"]
    if purpose in {"拡大", "軍備"}:
        cpu["army"] += rng.randint(2, 4)
        cpu["wealth"] += max(1, cpu["territory"])
    elif purpose in {"交易", "富国"}:
        cpu["wealth"] += rng.randint(3, 6)
        cpu["morale"] = min(100, cpu["morale"] + 1)
    elif purpose in {"守備", "生存"}:
        cpu["walls"] += rng.randint(1, 2)
        cpu["morale"] = min(100, cpu["morale"] + 2)
    else:
        cpu[rng.choice(("wealth", "army", "morale"))] += rng.randint(1, 3)
