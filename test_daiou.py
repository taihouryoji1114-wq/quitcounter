from core.daiou import (apply_policy, derived_identity, diplomatic_label,
                         end_turn, initial_game, map_cell, nation, normalize_game,
                         perform_map_action, relation, request_reinforcements,
                         strength)


def test_policy_advances_turn_and_is_deterministic_with_seed():
    game = initial_game()
    apply_policy(game, "guard", seed=1)
    assert game["turn"] == 2
    assert nation(game, "n0")["walls"] == 10


def test_new_world_uses_real_tokyo_regions_and_spreads_ten_capitals():
    game = initial_game()
    capitals = [cell for cell in game["map"] if cell["structure"] == "capital"]
    assert len(game["map"]) == 53
    assert len(capitals) == 10
    assert map_cell(game, "13122")["name"] == "葛飾区"
    assert map_cell(game, "13122")["owner"] == "n0"
    assert "13121" in map_cell(game, "13122")["neighbors"]


def test_old_grid_world_is_kept_as_recovery_snapshot():
    game = initial_game()
    game["map"] = [{"id": "r0c0", "row": 0, "col": 0, "owner": "n0", "troops": 19}]
    game.pop("map_kind")
    normalize_game(game)
    assert len(game["map"]) == 53
    assert game["legacy_grid_map"][0]["troops"] == 19
    assert game["version"] == 4


def test_large_country_has_cohesion_cost():
    game = initial_game()
    small = nation(game, "n0")
    large = dict(small, territory=8)
    assert strength(large) < strength(dict(large, territory=1))


def test_map_advance_requires_two_explicit_occupation_turns():
    game = initial_game()
    perform_map_action(game, "advance", "13122", "13121", seed=2)
    assert map_cell(game, "13121")["owner"] is None
    assert map_cell(game, "13121")["claim"]["owner"] == "n0"
    assert map_cell(game, "13121")["troops"] > 0

    end_turn(game, seed=2)
    perform_map_action(game, "occupy", "13121", seed=2)
    assert map_cell(game, "13121")["owner"] is None
    assert map_cell(game, "13121")["claim"]["progress"] == 1

    end_turn(game, seed=2)
    perform_map_action(game, "occupy", "13121", seed=2)
    assert map_cell(game, "13121")["owner"] == "n0"
    assert nation(game, "n0")["territory"] == 2
    assert game["turn"] == 3


def test_country_identity_is_created_by_actions():
    game = initial_game()
    player = nation(game, "n0")
    player["actions"]["trade"] = 3
    assert derived_identity(player) == "交易の国"


def test_old_save_receives_diplomacy_without_losing_progress():
    game = initial_game()
    game.pop("diplomacy")
    game.pop("coalition")
    game["turn"] = 9
    normalize_game(game)
    assert game["turn"] == 9
    assert game["diplomacy"] == {}
    assert game["coalition"] is None


def test_alliance_receives_troops_without_friendly_fire():
    game = initial_game()
    relation(game, "n0", "n1").update(status="alliance", trust=80)
    source = map_cell(game, "13122")
    target = map_cell(game, "13121")
    target.update(owner="n1", troops=2)
    before = source["troops"]
    message = perform_map_action(game, "advance", source["id"], target["id"], seed=3, march_troops=3)
    assert "援軍3" in message
    assert source["troops"] == before - 3
    assert target["troops"] == 5
    assert diplomatic_label(game, "n0", "n1") == "同盟"


def test_three_orders_are_planned_before_the_world_moves():
    game = initial_game()
    start_turn = game["turn"]
    perform_map_action(game, "recruit", "13122")
    perform_map_action(game, "recruit", "13122")
    perform_map_action(game, "recruit", "13122")
    assert game["turn"] == start_turn
    assert game["commands_left"] == 0
    try:
        perform_map_action(game, "recruit", "13122")
        assert False, "軍令上限を超えて行動できてしまった"
    except ValueError as error:
        assert "使い切りました" in str(error)
    end_turn(game, seed=1)
    assert game["turn"] == start_turn + 1
    assert game["commands_left"] == 3


def test_player_can_choose_exact_marching_troops_between_own_regions():
    game = initial_game()
    target = map_cell(game, "13121")
    target.update(owner="n0", troops=2, claim=None)
    source = map_cell(game, "13122")
    perform_map_action(game, "advance", source["id"], target["id"], march_troops=3)
    assert source["troops"] == 5
    assert target["troops"] == 5


def test_allied_reinforcements_reach_weakest_threatened_border():
    game = initial_game()
    relation(game, "n0", "n1").update(status="alliance", trust=80)
    border = map_cell(game, "13122")
    enemy = map_cell(game, "13121")
    enemy.update(owner="n2", troops=6)
    before = border["troops"]
    message = request_reinforcements(game, "n1", seed=1)
    assert border["troops"] > before
    assert "援軍" in message
    assert game["support_history"]["n1"] == game["turn"]


def test_allied_reinforcements_have_a_cooldown():
    game = initial_game()
    relation(game, "n0", "n1").update(status="alliance", trust=80)
    map_cell(game, "13121").update(owner="n2", troops=6)
    request_reinforcements(game, "n1", seed=1)
    try:
        request_reinforcements(game, "n1", seed=1)
        assert False, "同じターンに援軍を連続要請できてしまった"
    except ValueError as error:
        assert "再編中" in str(error)


def test_ambush_requires_a_forest_source_and_is_reported():
    game = initial_game()
    source = map_cell(game, "13122")
    source["terrain"] = "forest"
    map_cell(game, "13121").update(owner="n2", troops=2)
    message = perform_map_action(game, "advance", "13122", "13121", seed=1, tactic="ambush")
    assert "伏兵" in message


def test_pincer_requires_two_friendly_fronts():
    game = initial_game()
    target = map_cell(game, "13107")
    target.update(owner="n2", troops=2)
    second_front = map_cell(game, "13121")
    second_front.update(owner="n0", troops=4)
    message = perform_map_action(game, "advance", "13122", "13107", seed=1, tactic="pincer")
    assert "挟撃" in message
