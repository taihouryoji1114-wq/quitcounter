from core.daiou import (apply_policy, derived_identity, initial_game, map_cell,
                         nation, perform_map_action, strength)


def test_policy_advances_turn_and_is_deterministic_with_seed():
    game = initial_game()
    apply_policy(game, "guard", seed=1)
    assert game["turn"] == 2
    assert nation(game, "n0")["walls"] == 10


def test_large_country_has_cohesion_cost():
    game = initial_game()
    small = nation(game, "n0")
    large = dict(small, territory=8)
    assert strength(large) < strength(dict(large, territory=1))


def test_map_advance_claims_adjacent_neutral_land():
    game = initial_game()
    perform_map_action(game, "advance", "r0c0", "r0c1", seed=2)
    assert map_cell(game, "r0c1")["owner"] == "n0"
    assert nation(game, "n0")["territory"] == 2
    assert game["turn"] == 2


def test_country_identity_is_created_by_actions():
    game = initial_game()
    player = nation(game, "n0")
    player["actions"]["trade"] = 3
    assert derived_identity(player) == "交易の国"
