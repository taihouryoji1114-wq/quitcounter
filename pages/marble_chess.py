from nicegui import ui

from core.auth import require_app_access
from core.theme import Theme


@ui.page("/marble-chess")
def marble_chess_page():
    if not require_app_access("marble_chess"):
        return
    Theme.page("MARBLE CHESS", app_name="marble-chess")
    ui.add_head_html(
        '<link rel="stylesheet" href="/static/marble_chess.css?v=1">'
        '<link rel="stylesheet" href="/static/marble_chess_v2.css?v=7">'
        '<script src="/static/marble_chess.js?v=7" defer></script>'
    )
    ui.html("""
    <main id="mc-app" class="mc-app">
      <section id="mc-splash" class="mc-splash">
        <div class="mc-splash-shade"></div><div class="mc-splash-copy"><span>TACTICAL HP CHESS</span><h1>MARBLE<br>CHESS</h1><p>駒は、一撃では終わらない。</p><button id="mc-enter" class="mc-gold">ENTER</button></div>
      </section>
      <section id="mc-home" class="mc-home hidden">
        <div class="mc-home-head"><small>THE GRAND HALL</small><h1>MARBLE CHESS</h1><p>布陣を組み、王を討て。</p></div>
        <div class="mc-menu"><button id="mc-continue" class="hidden"><b>戦いを続ける</b><span>保存した盤面から再開</span></button><button id="mc-new"><b>レベルを選ぶ</b><span>LEVEL 1〜50・最大5勢力戦</span></button></div>
        <div class="mc-cost-rule"><b>布陣から始まる戦争</b><span>自軍2列なら配置は自由。射程・防壁・複数勢力の動きを読み、最後のキングを目指す。</span></div>
      </section>
      <section id="mc-stage-page" class="mc-page hidden"><header><button data-back>‹</button><div><small>CAMPAIGN</small><b>レベル選択</b></div><i></i></header><div class="mc-page-body mc-level-body"><div class="mc-level-legend"><span>1〜10　2勢力</span><span>11〜25　3勢力</span><span>26〜40　4勢力</span><span>41〜50　5勢力</span></div><div id="mc-level-grid" class="mc-level-grid"></div></div></section>
      <section id="mc-game" class="mc-game hidden">
        <header class="mc-game-head"><button id="mc-game-back">‹</button><div><small id="mc-turn-label">FORMATION</small><b id="mc-status">布陣を決める</b></div><button id="mc-help">?</button></header>
        <div id="mc-armies" class="mc-armies"></div>
        <div class="mc-command"><button id="mc-ready" class="mc-gold">この布陣で開戦</button><button id="mc-wall" class="mc-dark hidden">防壁を築く（残り3）</button></div>
        <div class="mc-board-wrap"><div id="mc-board" class="mc-board"></div></div>
        <div id="mc-unit-panel" class="mc-unit-panel"><span class="mc-panel-piece">♙</span><div><small>布陣</small><b>駒を選び、自軍2列内で入れ替え</b><p>初期配置は自由です</p></div></div>
        <div class="mc-battle-log"><span>BATTLE LOG</span><p id="mc-log">白軍の布陣が完了した。</p></div>
      </section>
      <div id="mc-modal" class="mc-modal hidden"><div><span id="mc-modal-mark">♔</span><h2 id="mc-modal-title"></h2><p id="mc-modal-text"></p><button id="mc-modal-sub" class="mc-dark hidden"></button><button id="mc-modal-main" class="mc-gold">閉じる</button></div></div>
    </main>
    """, sanitize=False).classes("w-full")
