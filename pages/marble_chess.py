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
        '<link rel="stylesheet" href="/static/marble_chess_v2.css?v=3">'
        '<script src="/static/marble_chess.js?v=3" defer></script>'
    )
    ui.html("""
    <main id="mc-app" class="mc-app">
      <section id="mc-splash" class="mc-splash">
        <div class="mc-splash-shade"></div><div class="mc-splash-copy"><span>TACTICAL HP CHESS</span><h1>MARBLE<br>CHESS</h1><p>駒は、一撃では終わらない。</p><button id="mc-enter" class="mc-gold">ENTER</button></div>
      </section>
      <section id="mc-home" class="mc-home hidden">
        <div class="mc-home-head"><small>THE GRAND HALL</small><h1>MARBLE CHESS</h1><p>布陣を組み、王を討て。</p></div>
        <div class="mc-menu"><button id="mc-continue" class="hidden"><b>対局を続ける</b><span>保存した盤面から再開</span></button><button id="mc-new"><b>CPU対局</b><span>通常盤・固定ダメージ</span></button><button id="mc-formation"><b>布陣</b><span>同じポーンでも能力が違う</span></button><button id="mc-collection"><b>駒コレクション</b><span>所有する駒と特性</span></button></div>
        <div class="mc-cost-rule"><b>対人戦構想</b><span>キングは必須・コスト0。強力な駒ほど高コストになり、合計100以内で布陣する。</span></div>
      </section>
      <section id="mc-formation-page" class="mc-page hidden"><header><button data-back>‹</button><div><small>FORMATION</small><b>布陣</b></div><i></i></header><div class="mc-page-body"><h2>8体のポーンを選ぶ</h2><p>青・金・赤の兵士キャラクターを組み合わせます。各枠をタップして変更。</p><div class="mc-budget"><span>編成コスト</span><b><em id="mc-cost">0</em> / 100</b></div><div id="mc-pawn-slots" class="mc-pawn-slots"></div><div class="mc-trait-legend"><b>3つの兵科</b><span>青・蒼刃兵：攻守のバランスに優れる</span><span>金・金剛衛士：高HP・王の隣で防御強化</span><span>赤・紅蓮突兵：高攻撃・低防御</span></div></div></section>
      <section id="mc-collection-page" class="mc-page hidden"><header><button data-back>‹</button><div><small>COLLECTION</small><b>駒コレクション</b></div><i></i></header><div class="mc-page-body"><div id="mc-cards" class="mc-cards"></div><div class="mc-coming"><b>ガチャは次期実装</b><p>N〜URまで、性能・特性・コストが固定された完成品の駒を追加予定。育成による能力差はありません。</p></div></div></section>
      <section id="mc-game" class="mc-game hidden">
        <header class="mc-game-head"><button id="mc-game-back">‹</button><div><small id="mc-turn-label">WHITE TURN</small><b id="mc-status">あなたの手番</b></div><button id="mc-help">?</button></header>
        <div class="mc-kings"><div><span>WHITE KING</span><b id="mc-white-king">160 / 160</b></div><div><span>BLACK KING</span><b id="mc-black-king">160 / 160</b></div></div>
        <div class="mc-board-wrap"><div id="mc-board" class="mc-board"></div></div>
        <div id="mc-unit-panel" class="mc-unit-panel"><span class="mc-panel-piece">♙</span><div><small>駒を選択</small><b>白の駒をタップ</b><p>光るマスへ通常のチェスと同じ動きで進みます</p></div></div>
        <div class="mc-battle-log"><span>BATTLE LOG</span><p id="mc-log">白軍の布陣が完了した。</p></div>
      </section>
      <div id="mc-modal" class="mc-modal hidden"><div><span id="mc-modal-mark">♔</span><h2 id="mc-modal-title"></h2><p id="mc-modal-text"></p><button id="mc-modal-sub" class="mc-dark hidden"></button><button id="mc-modal-main" class="mc-gold">閉じる</button></div></div>
    </main>
    """, sanitize=False).classes("w-full")
