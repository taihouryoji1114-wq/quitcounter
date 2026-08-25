import json
import random
import time

from nicegui import ui

from core.auth import has_permission, require_app_access
from core.store_quiz import store_quiz
from core.theme import Theme
from pages.store_common import store_header_actions


@ui.page("/store-ops/chanhaya")
def chanhaya_page():
    if not require_app_access("store_ops"):
        return
    Theme.page("ちゃんはや｜ちゃんこで早押しクイズ", app_name="store-ops")
    state = {"questions": [], "index": 0, "score": 0, "buzzed": False,
             "result": None, "started_at": 0.0, "finished": False,
             "player_name": ""}
    content = Theme.shell(
        "ちゃんはや", "ちゃんこで早押しクイズ",
        back_to="/store-ops", action=store_header_actions, brand="店舗運営",
    )
    with content:
        @ui.refreshable
        def game():
            if not state["questions"]:
                with ui.card().classes("chan-hero w-full q-pa-xl text-center"):
                    with ui.element("div").classes("chan-game-logo"):
                        ui.icon("bolt").classes("chan-logo-bolt")
                        ui.label("ちゃんはや").classes("chan-logo-title")
                    ui.label("ちゃんこで早押しクイズ").classes("chan-catch q-mt-md")
                    ui.label("知識と反射神経でハイスコアを狙え！").classes(
                        "text-xs text-white/70 q-mt-xs")
                    player_name = ui.input("プレイヤー名").props(
                        "outlined dark maxlength=16 inputmode=text").classes(
                            "chan-player-name w-full q-mt-lg")

                    def start_game():
                        name = str(player_name.value or "").strip()
                        if not name:
                            ui.notify("プレイヤー名を入力してください", type="warning")
                            return
                        custom = []
                        for item in store_quiz.questions():
                            choices = [item["answer"], *item.get("wrong_answers", [])]
                            if len(choices) == 4:
                                random.shuffle(choices)
                                custom.append((item["question"], tuple(choices), item["answer"]))
                        pool = custom
                        if not pool:
                            ui.notify("問題がまだ登録されていません", type="warning")
                            return
                        count = min(5, len(pool))
                        state.update(questions=random.sample(pool, count), index=0,
                                     score=0, buzzed=False, result=None,
                                     started_at=time.monotonic(), finished=False,
                                     player_name=name)
                        game.refresh()

                    ui.button("ひとり練習を始める", icon="play_arrow", on_click=start_game).props(
                        "unelevated no-caps").classes("chan-start w-full q-mt-xl")
                    if not store_quiz.questions():
                        ui.label("登録済みの問題は0問です").classes(
                            "text-xs text-amber-3 font-bold q-mt-md")
                        if has_permission("store_manage"):
                            ui.button("問題を登録する", icon="add", on_click=lambda: ui.navigate.to(
                                "/store-ops/settings")).props("flat no-caps color=amber")
                return
            if state["finished"]:
                with ui.card().classes("chan-result-card w-full q-pa-xl text-center"):
                    ui.icon("emoji_events").classes("text-6xl text-amber-7")
                    ui.label("RESULT").classes("text-[10px] tracking-[.3em] text-grey-6 q-mt-md")
                    ui.label(state["player_name"]).classes("text-sm text-amber-3 font-black")
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
                ui.label(f"Q {state['index'] + 1} / {len(state['questions'])}").classes("chan-progress")
                ui.label(f"SCORE {state['score']}").classes("chan-score")
            with ui.card().classes("chan-question-card w-full q-pa-lg"):
                question_label = ui.label("").classes("chan-question")
                countdown_label = ui.label("問題を読み上げ中…").classes(
                    "w-full text-center text-[10px] text-amber-3 font-black")
                if not state["buzzed"]:
                    def buzz():
                        state["buzzed"] = True
                        ui.run_javascript("window.chanHayaStop && window.chanHayaStop()")
                        game.refresh()

                    buzzer_button = ui.button("早押し！", on_click=buzz).props(
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

                if not state["buzzed"]:
                    question_json = json.dumps(question, ensure_ascii=False)
                    label_id = question_label.id
                    countdown_id = countdown_label.id
                    buzzer_id = buzzer_button.id
                    ui.timer(0.1, lambda: ui.run_javascript(f"""
                    (() => {{
                      window.chanHayaStop && window.chanHayaStop();
                      const text = {question_json};
                      const question = document.getElementById('c{label_id}');
                      const countdown = document.getElementById('c{countdown_id}');
                      let index = 0, remaining = 300, revealTimer, countdownTimer;
                      window.chanHayaStop = () => {{
                        clearInterval(revealTimer); clearInterval(countdownTimer);
                      }};
                      revealTimer = setInterval(() => {{
                        if (!question) return window.chanHayaStop();
                        index += 1; question.textContent = text.slice(0, index);
                        if (index >= text.length) {{
                          clearInterval(revealTimer);
                          if (countdown) countdown.textContent = '回答猶予 5:00';
                          countdownTimer = setInterval(() => {{
                            remaining -= 1;
                            if (countdown) countdown.textContent =
                              `回答猶予 ${{Math.floor(remaining / 60)}}:${{String(remaining % 60).padStart(2, '0')}}`;
                            if (remaining <= 0) {{
                              window.chanHayaStop();
                              const buzzer = document.getElementById('c{buzzer_id}');
                              if (buzzer) {{ buzzer.disabled = true; buzzer.style.opacity = '.35'; }}
                              if (countdown) countdown.textContent = '回答時間終了';
                            }}
                          }}, 1000);
                        }}
                      }}, 180);
                    }})()
                    """), once=True)

        game()
        ui.add_css("""
        body{background:radial-gradient(circle at 20% 5%,rgba(88,44,190,.55),transparent 34%),radial-gradient(circle at 85% 25%,rgba(255,47,109,.35),transparent 36%),linear-gradient(180deg,#100826,#071423 65%,#071B16)!important}.chan-hero,.chan-result-card{position:relative;overflow:hidden;border-radius:30px!important;background:linear-gradient(145deg,rgba(35,18,83,.97),rgba(8,30,50,.97))!important;border:1px solid rgba(255,215,91,.55)!important;box-shadow:0 20px 55px rgba(0,0,0,.4),inset 0 0 35px rgba(113,62,255,.18)!important;color:#fff!important}.chan-hero:before{content:'';position:absolute;inset:-70%;background:conic-gradient(transparent,#A863FF,transparent 18%,#FFCA4B,transparent 34%);animation:chan-spin 8s linear infinite;opacity:.15}.chan-hero>*{position:relative}.chan-game-logo{width:170px;height:170px;margin:auto;border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;background:radial-gradient(circle at 35% 25%,#FFEB79,#FF5E45 35%,#9D154D 66%,#35106E);border:7px solid #FFD968;box-shadow:0 0 0 5px #6B279C,0 0 38px rgba(255,93,198,.65),inset 0 4px 8px rgba(255,255,255,.55)}.chan-logo-bolt{font-size:61px!important;color:#fff;text-shadow:0 4px 0 #9D174B}.chan-logo-title{font-size:23px;font-weight:950;letter-spacing:-.08em;color:#FFF7A8!important;text-shadow:0 2px 4px #3A063A,0 0 13px #FFE166}.chan-player-name .q-field__label,.chan-player-name input{color:#fff!important}.chan-catch{font-size:24px;font-weight:950;color:#FFE77A;text-shadow:0 2px 9px rgba(255,218,65,.32)}.chan-start{min-height:58px!important;border:2px solid #FFE275!important;background:linear-gradient(135deg,#FF5B43,#D92272 55%,#7B25C8)!important;box-shadow:0 8px 0 #611660,0 14px 28px rgba(0,0,0,.34)!important;font-weight:950!important}.chan-progress,.chan-score{font-size:10px;font-weight:950;letter-spacing:.14em;color:#FFE06A}.chan-question-card{min-height:390px;border-radius:27px!important;background:linear-gradient(160deg,#21144A,#0D2843)!important;border:2px solid #7552C9!important;box-shadow:0 15px 36px rgba(0,0,0,.32),inset 0 0 25px rgba(112,75,220,.12)!important;color:#fff!important}.chan-question{min-height:92px;font-size:21px;font-weight:950;line-height:1.55;text-align:center;display:flex;align-items:center;justify-content:center;color:#fff}.chan-buzzer{display:flex!important;width:148px!important;height:148px!important;margin:34px auto 18px!important;border:9px solid #FFE171!important;background:radial-gradient(circle at 36% 26%,#FF9070,#F33255 60%,#991741)!important;color:#fff!important;font-size:25px!important;font-weight:950!important;box-shadow:0 15px 0 #6D173E,0 0 35px rgba(255,64,126,.55)!important}.chan-buzzer:active{transform:translateY(9px);box-shadow:0 6px 0 #6D173E,0 0 18px rgba(255,64,126,.55)!important}.chan-choice{min-height:51px!important;border-radius:14px!important;font-size:13px!important;font-weight:850!important;text-align:left!important;color:#fff!important;border-color:#8E79DA!important;background:rgba(255,255,255,.06)!important}@keyframes chan-spin{to{transform:rotate(360deg)}}
        """)
