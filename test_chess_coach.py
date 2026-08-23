import chess

from core.chess_coach import board_from, legal_targets, new_game, play_user_move, undo_full_turn


def test_opening_targets_are_legal():
    game=new_game()
    assert set(legal_targets(game,"e2"))=={"e3","e4"}
    assert legal_targets(game,"e7")==[]


def test_user_and_teacher_each_make_one_move():
    game=new_game(); play_user_move(game,"e2","e4",seed=1)
    assert len(game["history"])==2
    assert board_from(game).turn is chess.WHITE
    assert game["coach"]["candidates"]


def test_illegal_move_is_rejected():
    game=new_game()
    try:
        play_user_move(game,"e2","e5")
        assert False
    except ValueError as error:
        assert "動かせません" in str(error)


def test_undo_restores_position_before_player_move():
    game=new_game(); starting=game["fen"]
    play_user_move(game,"e2","e4",seed=1)
    undo_full_turn(game)
    assert game["fen"]==starting
    assert game["history"]==[]


def test_candidates_do_not_recommend_hanging_bishop_on_a6():
    game=new_game(); play_user_move(game,"e2","e4",seed=1)
    assert "f1 → a6" not in game["coach"]["candidates"]
