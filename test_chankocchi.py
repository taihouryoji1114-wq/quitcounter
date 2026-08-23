from datetime import datetime

import pytest

from core.chankocchi import (affection_label, can_depart, care, feed,
                             claim_store_reward, has_store_activity, initial_profile,
                             start_next_generation)


def test_care_rewards_only_once_per_action_and_day():
    profile = initial_profile(datetime(2026, 8, 23, 12, 0))
    first = care(profile, "meal", "2026-08-23")
    second = care(profile, "meal", "2026-08-23")
    assert first["gained"] is True
    assert second["gained"] is False
    assert profile["care_points"] == 1
    assert profile["affection"] == 2


def test_evolution_and_egg_are_based_on_active_care_days():
    profile = initial_profile()
    for day in range(1, 13):
        date = f"2026-08-{day:02d}"
        for action in ("meal", "play", "bath"):
            care(profile, action, date)
    assert profile["stage"] == 4
    assert profile["egg_ready"] is True


def test_next_generation_keeps_history_and_coins():
    profile = initial_profile()
    profile.update({"stage": 4, "egg_ready": True, "coins": 88,
                    "active_dates": [f"2026-08-{day:02d}" for day in range(1, 13)]})
    assert can_depart(profile)
    start_next_generation(profile, datetime(2026, 8, 23, 12, 0))
    assert profile["generation"] == 2
    assert profile["coins"] == 88
    assert len(profile["history"]) == 1


def test_store_reward_is_daily():
    profile = initial_profile()
    assert claim_store_reward(profile, "2026-08-23") == 10
    with pytest.raises(ValueError):
        claim_store_reward(profile, "2026-08-23")


def test_store_activity_detects_completed_shared_checklist():
    assert not has_store_activity({}, "2026-08-23")
    source = {"store_service_prep_records": {
        "2026-08-23": {"lunch": {"rice": "done"}}
    }}
    assert has_store_activity(source, "2026-08-23")


def test_affection_labels():
    assert affection_label(0) == "まだ少し緊張"
    assert affection_label(30) == "だいすき"


def test_food_choice_is_saved_and_changes_hunger():
    profile = initial_profile()
    profile["meters"]["hunger"] = 10
    feed(profile, "fish", "2026-08-23")
    assert profile["last_food"] == "fish"
    assert profile["meters"]["hunger"] == 38
