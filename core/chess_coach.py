"""Chess rules, a compact CPU opponent, and plain-Japanese move coaching."""

import math
import random

import chess


PIECE_VALUES = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
                chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}
PIECE_NAMES = {chess.PAWN: "ポーン", chess.KNIGHT: "ナイト", chess.BISHOP: "ビショップ",
               chess.ROOK: "ルーク", chess.QUEEN: "クイーン", chess.KING: "キング"}
CENTER = {chess.D4, chess.E4, chess.D5, chess.E5}


def new_game():
    return {"fen": chess.STARTING_FEN, "history": [], "coach": {
        "title": "最初の一手を考えよう", "verdict": "GUIDE",
        "summary": "中央を取り、ナイトとビショップを早めに働かせるのが基本です。",
        "why": "中央を押さえると、駒が左右どちらへも動きやすくなります。",
        "danger": "同じ駒ばかり動かすと、ほかの駒が眠ったままになります。",
        "candidates": ["e2 → e4", "d2 → d4", "g1 → f3"]}}


def board_from(game):
    try: return chess.Board(game.get("fen", chess.STARTING_FEN))
    except (ValueError, TypeError): return chess.Board()


def legal_targets(game, square_name):
    board = board_from(game)
    try: source = chess.parse_square(square_name)
    except ValueError: return []
    return [chess.square_name(move.to_square) for move in board.legal_moves if move.from_square == source]


def _score(board):
    if board.is_checkmate(): return -100000 if board.turn else 100000
    score = 0
    for kind, value in PIECE_VALUES.items():
        score += len(board.pieces(kind, chess.WHITE)) * value
        score -= len(board.pieces(kind, chess.BLACK)) * value
    score += sum(12 if sq in CENTER else 0 for sq in board.pieces(chess.PAWN, chess.WHITE))
    score -= sum(12 if sq in CENTER else 0 for sq in board.pieces(chess.PAWN, chess.BLACK))
    mobility = board.legal_moves.count()
    score += mobility if board.turn == chess.WHITE else -mobility
    return score


def _minimax(board, depth, alpha, beta):
    if depth == 0 or board.is_game_over(): return _score(board)
    if board.turn:
        value = -math.inf
        for move in board.legal_moves:
            board.push(move); value = max(value, _minimax(board, depth-1, alpha, beta)); board.pop()
            alpha = max(alpha, value)
            if beta <= alpha: break
        return value
    value = math.inf
    for move in board.legal_moves:
        board.push(move); value = min(value, _minimax(board, depth-1, alpha, beta)); board.pop()
        beta = min(beta, value)
        if beta <= alpha: break
    return value


def cpu_move(board, seed=None):
    rng = random.Random(seed)
    moves = list(board.legal_moves)
    if not moves: return None
    ranked = []
    for move in moves:
        board.push(move); ranked.append((_minimax(board, 1, -math.inf, math.inf), rng.random(), move)); board.pop()
    return min(ranked, key=lambda item: (item[0], item[1]))[2]


def _move_text(move):
    return f"{chess.square_name(move.from_square)} → {chess.square_name(move.to_square)}"


def explain_move(before, move, actor="あなた"):
    piece = before.piece_at(move.from_square)
    captured = before.piece_at(move.to_square)
    name = PIECE_NAMES.get(piece.piece_type, "駒")
    reasons, cautions = [], []
    if captured: reasons.append(f"相手の{PIECE_NAMES[captured.piece_type]}を取り、駒得を狙いました")
    if move.to_square in CENTER: reasons.append("中央に影響を与え、動ける場所を増やしました")
    if before.is_castling(move): reasons.append("キャスリングでキングを守り、ルークも働かせました")
    if piece.piece_type in {chess.KNIGHT, chess.BISHOP} and chess.square_rank(move.from_square) in {0, 7}:
        reasons.append(f"{name}を初期位置から出し、攻撃に参加させました")
    after = before.copy(); after.push(move)
    if after.is_check(): reasons.append("相手キングへチェックをかけ、応手を限定しました")
    attackers = after.attackers(not after.turn, move.to_square)
    defenders = after.attackers(after.turn, move.to_square)
    if attackers and not defenders: cautions.append(f"移動先の{name}が相手に狙われています")
    elif attackers:
        cheapest=min((PIECE_VALUES[after.piece_at(sq).piece_type] for sq in attackers),default=9999)
        if cheapest<=PIECE_VALUES[piece.piece_type]:
            cautions.append(f"{name}は次に取られる可能性があります。交換して得かまで確認が必要です")
    if not reasons: reasons.append(f"{name}の位置を変え、次の展開を作る一手です")
    if not cautions: cautions.append("次は相手の狙いを確認してから、自分の攻撃を続けましょう")
    return reasons, cautions


def candidate_moves(board, count=3):
    scored=[]
    for move in board.legal_moves:
        piece=board.piece_at(move.from_square); captured=board.piece_at(move.to_square)
        bonus=0
        if move.to_square in CENTER: bonus+=28
        if captured: bonus+=PIECE_VALUES[captured.piece_type]//8
        if piece.piece_type in {chess.KNIGHT,chess.BISHOP} and chess.square_rank(move.from_square) in {0,7}: bonus+=36
        if piece.piece_type==chess.QUEEN and len(board.move_stack)<8: bonus-=45
        board.push(move)
        if board.is_check(): bonus+=14
        # 候補手は相手の最善の返しまで読む。単に「駒を出した」だけの手を
        # 高評価にしないため、静的評価ではなく1手先のミニマックスを使う。
        score=_minimax(board,1,-math.inf,math.inf)+(bonus if not board.turn else -bonus)
        board.pop()
        scored.append((score, move))
    scored.sort(key=lambda item:item[0], reverse=board.turn)
    return [_move_text(move) for _, move in scored[:count]]


def _ranked_moves(board):
    """Return legal moves ordered for the side to move, with one reply considered."""
    ranked=[]
    for move in board.legal_moves:
        board.push(move)
        value=_minimax(board,1,-math.inf,math.inf)
        board.pop()
        ranked.append((value,move))
    ranked.sort(key=lambda item:item[0],reverse=board.turn)
    return [move for _,move in ranked]


def explore_plans(board, count=3, plies=5):
    """Build compact, non-destructive principal variations for research mode."""
    plans=[]
    for first in _ranked_moves(board)[:count]:
        branch=board.copy(); first_before=branch.copy()
        reasons,cautions=explain_move(first_before,first)
        first_san=first_before.san(first); branch.push(first)
        line=[first_san]
        for _ in range(max(0,plies-1)):
            ranked=_ranked_moves(branch)
            if not ranked: break
            reply=ranked[0]; line.append(branch.san(reply)); branch.push(reply)
        change=_score(branch)-_score(board)
        benefit=change if board.turn else -change
        verdict="狙いが通れば有力" if benefit>90 else ("相手に正確に返されると苦しい" if benefit<-90 else "十分に検討できる計画")
        plans.append({"move":_move_text(first),"san":first_san,"uci":first.uci(),
            "idea":" / ".join(reasons),"risk":" / ".join(cautions),
            "line":" → ".join(line),"verdict":verdict,
            "note":"この手順は代表例です。相手の応手が変われば、別の狙いへ切り替える必要があります。"})
    return plans


def play_user_move(game, source, target, seed=None):
    board = board_from(game)
    if not board.turn: raise ValueError("相手の手番です。")
    candidates = [m for m in board.legal_moves if chess.square_name(m.from_square)==source and chess.square_name(m.to_square)==target]
    if not candidates: raise ValueError("その駒はそこへ動かせません。光っているマスから選んでください。")
    move = next((m for m in candidates if m.promotion==chess.QUEEN), candidates[0])
    before=board.copy(); user_reasons,user_cautions=explain_move(before,move)
    san=before.san(move); board.push(move)
    game.setdefault("history",[]).append({"side":"あなた","move":san,"from":source,"to":target,"fen_before":before.fen()})
    if board.is_game_over():
        title="勝利！" if board.is_checkmate() else "対局終了"
        game["fen"]=board.fen(); game["coach"]={"title":title,"verdict":"FINISH","summary":"最後まで指し切りました。","why":" / ".join(user_reasons),"danger":" / ".join(user_cautions),"candidates":[]}; return
    reply=cpu_move(board,seed)
    cpu_before=board.copy(); cpu_reasons,cpu_cautions=explain_move(cpu_before,reply,"先生")
    cpu_san=cpu_before.san(reply); board.push(reply)
    game["history"].append({"side":"先生","move":cpu_san,"from":chess.square_name(reply.from_square),"to":chess.square_name(reply.to_square),"fen_before":cpu_before.fen()})
    delta=_score(board)-_score(chess.Board())
    verdict="GOOD" if delta>=-80 else ("CAREFUL" if delta>=-220 else "RETHINK")
    labels={"GOOD":"いい一手","CAREFUL":"少し注意","RETHINK":"考え直せる一手"}
    game["coach"]={"title":labels[verdict],"verdict":verdict,
        "summary":f"あなたは {san}。先生は {cpu_san} と返しました。",
        "why":" / ".join(user_reasons),
        "danger":f"相手の意図：{' / '.join(cpu_reasons)}。{' / '.join(user_cautions)}",
        "candidates":candidate_moves(board)}
    game["fen"]=board.fen()


def undo_full_turn(game):
    """Undo the teacher reply and the player's preceding move."""
    history=game.setdefault("history",[])
    user_index=next((i for i in range(len(history)-1,-1,-1) if history[i].get("side")=="あなた"),None)
    if user_index is None: raise ValueError("まだ戻せる手がありません。")
    fen=history[user_index].get("fen_before")
    if not fen: raise ValueError("この対局の古い手は戻せません。次の一手から利用できます。")
    del history[user_index:]
    game["fen"]=fen
    game["coach"]={"title":"一手戻しました","verdict":"GUIDE",
        "summary":"別の考え方を試してみましょう。","why":"失敗を戻して比較することも、上達の大切な練習です。",
        "danger":"相手の次の一手を予想してから指してみましょう。","candidates":candidate_moves(chess.Board(fen))}
