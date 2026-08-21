from nicegui import ui

from core.auth import require_app_access
from core.theme import Theme


@ui.page("/gunryakugoma")
def gunryakugoma_page():
    if not require_app_access("gunryakugoma"):
        return
    Theme.page("軍略駒", app_name="gunryakugoma")
    ui.add_head_html(
        '<link rel="stylesheet" href="/static/gunryakugoma.css?v=6">'
        '<script src="/static/gunryakugoma.js?v=6" defer></script>'
    )
    ui.html(
        """
        <main id="sk-app" class="sk-app">
          <section id="sk-home" class="sk-home">
            <div class="sk-home-shade"></div>
            <button id="gun-home-exit" class="sk-exit" type="button" aria-label="R-BASEへ戻る">⌂</button>
            <div class="sk-home-copy">
              <span class="sk-eyebrow">TURN-BASED STRATEGY</span>
              <h1>軍略駒</h1>
              <p>兵糧を読み、陣を築き、敵将を討て。</p>
              <button id="sk-start" class="sk-primary" type="button">初陣を始める</button>
              <div class="sk-victory-note"><b>勝利条件</b><span>敵将を討つ、または敵本陣を破壊</span></div>
            </div>
          </section>

          <section id="sk-game" class="sk-game is-hidden">
            <header class="sk-topbar">
              <button id="sk-home-btn" class="sk-icon-btn" type="button" aria-label="ホームへ戻る">‹</button>
              <div class="sk-turn-title"><small>第 <span id="sk-turn">1</span> ターン</small><strong id="sk-phase">あなたの軍議</strong></div>
              <button id="sk-help" class="sk-icon-btn" type="button" aria-label="遊び方">?</button>
            </header>

            <div class="sk-resource-bar">
              <div><span>軍資金</span><strong id="sk-money">4,000</strong><i>両</i></div>
              <div><span>兵糧</span><strong id="sk-food">7,000</strong><i>俵</i></div>
              <div><span>領地収入</span><strong id="sk-income">+1,000</strong><i>/ターン</i></div>
            </div>

            <div class="sk-battle-wrap">
              <div class="sk-enemy-banner"><span>朱雀軍</span><b id="sk-enemy-status">敵将健在</b></div>
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
                <button id="sk-build" type="button"><i>⌂</i><span>築城・柵</span></button>
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
