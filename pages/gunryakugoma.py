import json
from datetime import datetime

from nicegui import ui

from core.auth import require_app_access, selected_user_id
from core.data import data
from core.theme import Theme


@ui.page("/gunryakugoma")
def gunryakugoma_page():
    if not require_app_access("gunryakugoma"):
        return
    user_id = selected_user_id()
    profiles = data.data.setdefault("gunryakugoma", {}).setdefault("profiles", {})
    server_profile = profiles.get(user_id, {})

    def save_profile(event):
        value = event.args if isinstance(event.args, dict) else {}
        conquered = value.get("conquered", ["katsushika"])
        if not isinstance(conquered, list):
            conquered = ["katsushika"]
        conquered = [str(item) for item in conquered[:16]]
        if "katsushika" not in conquered:
            conquered.insert(0, "katsushika")
        safe_profile = {
            "wins": max(0, int(value.get("wins", 0))),
            "territories": len(conquered),
            "level": max(1, int(value.get("level", 1))),
            "xp": max(0, int(value.get("xp", 0))),
            "command": "cavalry",
            "conquered": conquered,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        profiles[user_id] = safe_profile
        data.save()

    ui.on("gunryaku_profile_save", save_profile)
    Theme.page("軍略駒", app_name="gunryakugoma")
    encoded_profile = json.dumps(server_profile, ensure_ascii=False).replace("<", "\\u003c")
    ui.add_head_html(
        f'<script>window.GUNRYAKU_SERVER_PROFILE={encoded_profile};</script>'
        '<link rel="stylesheet" href="/static/gunryakugoma.css?v=13">'
        '<script src="/static/gunryakugoma.js?v=14" defer></script>'
    )
    ui.html(
        """
        <main id="sk-app" class="sk-app">
          <section id="sk-splash" class="sk-splash">
            <div class="sk-splash-shade"></div>
            <div class="sk-splash-copy">
              <span>VERSION 0.7 · EMPIRE AWAKENS</span>
              <h1>軍略駒</h1>
              <p>一駒より、天下を築け。</p>
              <button id="sk-enter" class="sk-primary" type="button">軍略を始める</button>
            </div>
          </section>

          <section id="sk-home" class="sk-home is-hidden">
            <div class="sk-home-shade"></div>
            <div class="sk-home-copy">
              <span class="sk-eyebrow">SORYU EMPIRE</span>
              <h1>帝国軍議</h1>
              <p>領土を治め、武将を率い、日本統一へ。</p>
              <div class="sk-empire-status"><div><small>蒼龍帝国</small><b><span id="sk-territories">1</span>国</b></div><div><small>戦勝</small><b><span id="sk-wins">0</span>回</b></div></div>
              <div class="sk-hub-menu"><button id="sk-resume" class="sk-hub-card is-hidden" type="button"><b>戦を続ける</b><span>保存された戦場へ戻る</span></button><button id="sk-roster-btn" class="sk-hub-card" type="button"><b>武将一覧</b><span>武将の能力と得意兵種を確認</span></button></div>
              <section class="sk-campaign">
                <div class="sk-campaign-heading"><div><small>CAMPAIGN MAP</small><b>日本統一</b></div><span id="sk-unification">1 / 16</span></div>
                <div id="sk-campaign-map" class="sk-campaign-map" aria-label="日本攻略マップ"></div>
                <div class="sk-faction-legend"><span class="soryu">蒼龍帝国</span><span class="suzaku">朱雀同盟</span><span class="genbu">玄武連邦</span><span class="byakko">白虎軍</span></div>
                <div class="sk-next-battle"><small>次の戦場</small><b id="sk-selected-province">武蔵</b><span id="sk-selected-detail">関東平野の要衝</span></div>
                <button id="sk-start" class="sk-primary" type="button">選択した領土へ出陣</button>
              </section>
              <div class="sk-victory-note"><b>勝利条件</b><span>敵将を討つ、または敵本陣を破壊</span></div>
            </div>
          </section>

          <section id="sk-roster" class="sk-roster is-hidden">
            <header class="sk-topbar"><button id="sk-roster-back" class="sk-icon-btn" type="button">‹</button><div class="sk-turn-title"><small>COMMANDERS</small><strong>武将一覧</strong></div><span class="sk-top-spacer"></span></header>
            <div class="sk-roster-body"><section class="sk-commander-card">
              <div class="sk-card-rarity">UR</div>
              <div class="sk-commander-copy"><small>蒼龍軍総大将</small><b>蒼牙</b><span>Lv.<strong id="sk-commander-level">1</strong> · EXP <strong id="sk-commander-xp">0</strong>/<strong id="sk-commander-next">100</strong></span></div>
              <div class="sk-card-skill"><small>固有技能</small><b>蒼騎の号令</b><span>騎兵の攻撃 +<strong id="sk-command-bonus">18</strong>%</span></div>
              <div class="sk-command-type"><small>固定の得意兵種</small><strong>騎馬</strong></div>
            </section><div class="sk-roster-note"><b>武将召喚</b><p>騎兵を招集すると蒼牙を配属できます。武将の付いた軍は、同じ兵数でも高い戦力を発揮します。</p></div></div>
          </section>

          <section id="sk-game" class="sk-game is-hidden">
            <header class="sk-topbar">
              <button id="sk-home-btn" class="sk-icon-btn" type="button" aria-label="戦場選択へ戻る">‹</button>
              <div class="sk-turn-title"><small>第 <span id="sk-turn">1</span> ターン</small><strong id="sk-phase">あなたの軍議</strong></div>
              <button id="sk-help" class="sk-icon-btn" type="button" aria-label="遊び方">?</button>
            </header>

            <div class="sk-resource-bar">
              <div><span>軍資金</span><strong id="sk-money">4,000</strong><i>両</i></div>
              <div><span>兵糧</span><strong id="sk-food">7,000</strong><i>俵</i></div>
              <div><span>領地収入</span><strong id="sk-income">+1,000</strong><i>/ターン</i></div>
              <div><span>軍の維持</span><strong id="sk-upkeep">-105</strong><i>俵/ターン</i></div>
            </div>

            <div class="sk-battle-wrap">
              <div class="sk-enemy-banner"><span id="sk-enemy-name">朱雀軍</span><b id="sk-enemy-status">敵将健在</b></div>
              <div class="sk-force-summary"><div><b>蒼龍軍</b><span>将 <strong id="sk-player-general">0</strong></span><span>歩 <strong id="sk-player-infantry">0</strong></span><span>騎 <strong id="sk-player-cavalry">0</strong></span><span>弓 <strong id="sk-player-archer">0</strong></span></div><div><b>朱雀軍</b><span>将 <strong id="sk-enemy-general">0</strong></span><span>歩 <strong id="sk-enemy-infantry">0</strong></span><span>騎 <strong id="sk-enemy-cavalry">0</strong></span><span>弓 <strong id="sk-enemy-archer">0</strong></span></div></div>
              <div id="sk-board" class="sk-board" aria-label="軍略盤"></div>
              <div class="sk-player-banner"><span>蒼龍軍</span><b id="sk-player-status">敵陣を攻略せよ</b></div>
            </div>

            <section class="sk-command">
              <div id="sk-selection" class="sk-selection">
                <span class="sk-selection-icon">軍</span>
                <div><small>軍略</small><strong>動かす駒を選択</strong><p>自軍の駒をタップしてください</p></div>
              </div>
              <div class="sk-actions">
                <button id="sk-recruit" type="button"><i>＋</i><span>兵を招集</span></button>
                <button id="sk-build" type="button"><i>⌂</i><span>施設建設</span></button>
                <button id="sk-cancel" type="button"><i>×</i><span>選択解除</span></button>
                <button id="sk-end-turn" class="is-accent" type="button"><i>»</i><span>ターン終了</span></button>
              </div>
            </section>

            <div id="sk-panel" class="sk-panel is-hidden"></div>
            <div class="sk-log"><span>戦況</span><p id="sk-log">城から軍資金と兵糧が届いた。</p></div>
          </section>

          <div id="sk-modal" class="sk-modal is-hidden" role="dialog" aria-modal="true">
            <div class="sk-modal-card">
              <span id="sk-modal-mark" class="sk-modal-mark">軍</span>
              <h2 id="sk-modal-title">軍略駒</h2>
              <p id="sk-modal-text"></p>
              <button id="sk-modal-secondary" class="sk-secondary is-hidden" type="button">やめる</button>
              <button id="sk-modal-primary" class="sk-primary" type="button">閉じる</button>
            </div>
          </div>
        </main>
        """,
        sanitize=False,
    ).classes("w-full")
