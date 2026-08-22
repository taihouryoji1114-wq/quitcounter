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
        '<link rel="stylesheet" href="/static/marble_chess_v2.css?v=5">'
        '<script src="/static/marble_chess.js?v=5" defer></script>'
    )
    ui.html("""
    <main id="mc-app" class="mc-app">
      <section id="mc-splash" class="mc-splash">
        <div class="mc-splash-shade"></div><div class="mc-splash-copy"><span>TACTICAL HP CHESS</span><h1>MARBLE<br>CHESS</h1><p>駒は、一撃では終わらない。</p><button id="mc-enter" class="mc-gold">ENTER</button></div>
      </section>
      <section id="mc-home" class="mc-home hidden">
        <div class="mc-home-head"><small>THE GRAND HALL</small><h1>MARBLE CHESS</h1><p>布陣を組み、王を討て。</p></div>
        <div class="mc-menu"><button id="mc-continue" class="hidden"><b>対局を続ける</b><span>保存した盤面から再開</span></button><button id="mc-new"><b>対局を始める</b><span>CPU戦・同じ端末で2人対戦</span></button><button id="mc-collection"><b>役職キャラクター</b><span>ガチャ対象の役職駒を確認</span></button></div>
        <div class="mc-cost-rule"><b>対人戦構想</b><span>キングは必須・コスト0。強力な駒ほど高コストになり、合計100以内で布陣する。</span></div>
      </section>
      <section id="mc-stage-page" class="mc-page hidden"><header><button data-back>‹</button><div><small>BATTLEFIELD</small><b>対局を選択</b></div><i></i></header><div class="mc-page-body"><div class="mc-stage-grid"><button data-stage="standard" data-mode="cpu"><small>CPU BATTLE</small><b>王都の大理石盤</b><span>8×8・CPU対戦<br>基本ルールで戦う標準戦</span></button><button data-stage="grand" data-mode="cpu"><small>CPU BATTLE</small><b>帝国大戦場</b><span>10×10・同じコスト上限<br>駒数は増やさず広い盤面で戦う</span></button><button data-stage="standard" data-mode="local"><small>LOCAL 2 PLAYERS</small><b>王都の対人盤</b><span>8×8・同じ端末を交互に操作</span></button><button data-stage="grand" data-mode="local"><small>LOCAL 2 PLAYERS</small><b>帝国の対人盤</b><span>10×10・オフライン2人対戦</span></button></div><div class="mc-coming"><b>オンライン対戦は今後</b><p>今回は通信を使わず、1台の端末を交互に操作するローカル2人対戦です。</p></div></div></section>
      <section id="mc-collection-page" class="mc-page hidden"><header><button data-back>‹</button><div><small>COLLECTION</small><b>役職キャラクター</b></div><i></i></header><div class="mc-page-body"><div id="mc-cards" class="mc-cards"></div><div class="mc-coming"><b>ガチャ対象は役職駒だけ</b><p>キング・クイーン・ルーク・ビショップ・ナイトを中心に展開。ポーンは特性のない通常歩兵に統一します。</p></div></div></section>
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
