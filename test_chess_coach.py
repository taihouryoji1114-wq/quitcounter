import chess

from core.chess_coach import board_from, legal_targets, new_game, play_user_move


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
