import random
import time

from nicegui import ui

from core.auth import require_app_access
from core.theme import Theme
from pages.store_common import store_header_actions


QUESTIONS = (
    ("発注してほしい物を見つけた時、スタッフが入力する場所は？",
     ("発注依頼", "仕入れリスト", "在庫確認", "自由引き継ぎ"), "発注依頼"),
    ("その日に残った作業や連絡を、次の営業へ残す場所は？",
     ("自由引き継ぎ", "売上入力", "温度・衛生", "商品登録"), "自由引き継ぎ"),
    ("食材や備品の現在数を記録する画面は？",
     ("在庫確認", "仕入れリスト", "今日のチェック表", "イベント"), "在庫確認"),
    ("仕込みや日々の作業を確認する画面は？",
     ("今日のチェック表", "シフト提出", "マニュアル", "仕入れリスト"), "今日のチェック表"),
    ("冷蔵庫や冷凍庫の温度を記録する画面は？",
     ("温度・衛生", "在庫確認", "清掃", "発注依頼"), "温度・衛生"),
    ("実際に買う商品と個数をまとめる管理用の画面は？",
     ("仕入れリスト", "発注依頼", "在庫確認", "自由引き継ぎ"), "仕入れリスト"),
    ("間違えて登録した商品や仕込み項目を直す場所は？",
     ("登録・設定", "ホーム", "イベント", "衛生記録"), "登録・設定"),
    ("発注依頼を完了にできるのは？",
     ("管理者", "入力した本人だけ", "全スタッフ", "誰もできない"), "管理者"),
    ("引き継ぎボードに分かれて表示されるものは？",
     ("仕込み・自由引き継ぎ・発注", "売上・利益・税金", "出勤・退勤・休憩", "予定だけ"),
     "仕込み・自由引き継ぎ・発注"),
    ("店舗の予定や親睦イベントを確認する場所は？",
     ("イベントスケジュール", "仕入れリスト", "温度・衛生", "在庫確認"),
     "イベントスケジュール"),
)


@ui.page("/store-ops/chanhaya")
def chanhaya_page():
    if not require_app_access("store_ops"):
        return
    Theme.page("ちゃんはや｜店舗運営", app_name="store-ops")
    state = {"questions": [], "index": 0, "score": 0, "buzzed": False,
             "result": None, "started_at": 0.0, "finished": False}
    content = Theme.shell(
        "ちゃんはや", "店舗みんなの早押しクイズ",
        back_to="/store-ops", action=store_header_actions, brand="店舗運営",
    )
    with content:
        @ui.refreshable
        def game():
            if not state["questions"]:
                with ui.card().classes("chan-hero w-full q-pa-xl text-center"):
                    ui.icon("bolt").classes("chan-logo")
                    ui.label("知って、押して、強くなる。 ").classes("text-2xl font-black q-mt-md")
                    ui.label("全5問・正解＋10点・不正解−5点").classes(
                        "text-xs text-grey-6 q-mt-xs")

                    def start_game():
                        state.update(questions=random.sample(list(QUESTIONS), 5), index=0,
                                     score=0, buzzed=False, result=None,
                                     started_at=time.monotonic(), finished=False)
                        game.refresh()

                    ui.button("ひとり練習を始める", icon="play_arrow", on_click=start_game).props(
                        "unelevated no-caps").classes("chan-start w-full q-mt-xl")
                return
            if state["finished"]:
                with ui.card().classes("chan-result-card w-full q-pa-xl text-center"):
                    ui.icon("emoji_events").classes("text-6xl text-amber-7")
                    ui.label("RESULT").classes("text-[10px] tracking-[.3em] text-grey-6 q-mt-md")
                    ui.label(f"{state['score']}点").classes("text-5xl font-black")
                    message = "店舗マスター！" if state["score"] >= 45 else (
                        "かなりいい感じ！" if state["score"] >= 30 else "もう一度挑戦しよう！")
                    ui.label(message).classes("text-lg font-black q-mt-sm")
                    ui.button("もう一度", icon="replay", on_click=lambda: (
                        state.update(questions=[]), game.refresh())).props(
                            "unelevated no-caps").classes("w-full q-mt-xl")
                return

            question, choices, answer = state["questions"][state["index"]]
            with ui.row().classes("w-full items-center justify-between q-mb-sm"):
                ui.label(f"Q {state['index'] + 1} / 5").classes("chan-progress")
                ui.label(f"SCORE {state['score']}").classes("chan-score")
            with ui.card().classes("chan-question-card w-full q-pa-lg"):
                ui.label(question).classes("chan-question")
                if not state["buzzed"]:
                    def buzz():
                        state["buzzed"] = True
                        game.refresh()

                    ui.button("早押し！", on_click=buzz).props(
                        "round unelevated aria-label='早押しボタン'").classes("chan-buzzer")
                    ui.label("答えが分かったら押して！").classes(
                        "w-full text-center text-[10px] text-grey-6")
                elif state["result"] is None:
                    with ui.column().classes("w-full gap-2 q-mt-lg"):
                        for choice in choices:
                            def answer_question(_, selected=choice):
                                correct = selected == answer
                                state["score"] += 10 if correct else -5
                                state["result"] = (correct, selected, answer)
                                game.refresh()

                            ui.button(choice, on_click=answer_question).props(
                                "outline no-caps align=left").classes("chan-choice w-full")
                else:
                    correct, selected, correct_answer = state["result"]
                    ui.icon("check_circle" if correct else "cancel").classes(
                        "text-6xl q-mx-auto q-mt-lg " +
                        ("text-positive" if correct else "text-negative"))
                    ui.label("正解！ ＋10" if correct else "不正解 −5").classes(
                        "w-full text-center text-xl font-black")
                    if not correct:
                        ui.label(f"正解は「{correct_answer}」").classes(
                            "w-full text-center text-sm text-grey-7 q-mt-xs")

                    def next_question():
                        state["index"] += 1
                        state["buzzed"] = False
                        state["result"] = None
                        if state["index"] >= len(state["questions"]):
                            state["finished"] = True
                        game.refresh()

                    ui.button("次の問題", icon="arrow_forward", on_click=next_question).props(
                        "unelevated no-caps").classes("w-full q-mt-lg")

        game()
        ui.add_css("""
        body{background:radial-gradient(circle at 50% 0,#FFF0D8,transparent 35%),linear-gradient(180deg,#F8F3EA,#EEF3EF)!important}.chan-hero,.chan-result-card{border-radius:30px!important;background:rgba(255,255,255,.94)!important;border:1px solid #F0D8AF!important;box-shadow:0 20px 55px rgba(86,58,22,.12)!important}.chan-logo{display:flex!important;align-items:center;justify-content:center;width:94px;height:94px;margin:auto;border-radius:50%;font-size:58px!important;color:#fff;background:radial-gradient(circle at 36% 28%,#FFDA60,#F05A36 62%,#B9232C);box-shadow:0 13px 28px rgba(197,58,39,.32),inset 0 3px 7px rgba(255,255,255,.5)}.chan-start{min-height:56px!important;background:linear-gradient(135deg,#EF6A35,#C62F36)!important}.chan-progress,.chan-score{font-size:10px;font-weight:950;letter-spacing:.14em;color:#7C5B38}.chan-question-card{min-height:390px;border-radius:27px!important;background:#fff!important;border:1px solid #EEE4D4!important;box-shadow:0 15px 36px rgba(62,52,35,.09)!important}.chan-question{min-height:92px;font-size:21px;font-weight:950;line-height:1.55;text-align:center;display:flex;align-items:center;justify-content:center}.chan-buzzer{display:flex!important;width:148px!important;height:148px!important;margin:34px auto 18px!important;border:9px solid #FFE7D1!important;background:radial-gradient(circle at 36% 26%,#FF8A56,#E53D37 60%,#A7192C)!important;color:#fff!important;font-size:25px!important;font-weight:950!important;box-shadow:0 15px 0 #8E2630,0 22px 35px rgba(137,35,43,.3)!important}.chan-buzzer:active{transform:translateY(9px);box-shadow:0 6px 0 #8E2630,0 12px 20px rgba(137,35,43,.25)!important}.chan-choice{min-height:51px!important;border-radius:14px!important;font-size:13px!important;font-weight:850!important;text-align:left!important}
        """)
