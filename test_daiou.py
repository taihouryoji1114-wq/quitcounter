from core.daiou import apply_policy, initial_game, nation, strength


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
