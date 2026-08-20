from nicegui import ui

from core.auth import require_app_access
from core.theme import Theme


GAME_HTML = r'''
<div id="ge-app" class="ge-app">
  <div class="ge-top">
    <button class="ge-back" onclick="location.href='/'">‹</button>
    <div><b>GRID EMPIRE</b><small>領土戦線</small></div>
    <button id="ge-restart" class="ge-restart">↻</button>
  </div>
  <div class="ge-score">
    <div class="blue"><span>自軍</span><b id="ge-blue">0</b></div>
    <div class="turn"><b id="ge-state">戦闘開始</b><small id="ge-hint">自分のマスを選択</small></div>
    <div class="red"><span>敵軍</span><b id="ge-red">0</b></div>
  </div>
  <div class="ge-board-wrap"><div id="ge-board" class="ge-board"></div></div>
  <div class="ge-legend"><span><i class="blue"></i>自軍</span><span><i class="red"></i>敵軍</span><span><i class="neutral"></i>未占領</span><span>★ 首都</span></div>
  <div class="ge-help"><b>遊び方</b><span>青い領地を選び、隣の陸地をタップして侵攻。数字は兵力。敵の★首都を奪えば勝利。</span></div>
  <div id="ge-modal" class="ge-modal"><div><b id="ge-result"></b><span id="ge-result-sub"></span><button id="ge-again">もう一度</button></div></div>
</div>
'''


GAME_CSS = r'''
<style>
body{margin:0;background:#081525!important;color:#fff;overscroll-behavior:none}.nicegui-content{padding:0!important}
.ge-app{min-height:100dvh;background:radial-gradient(circle at 50% 0,#163252 0,#081525 48%,#050b14 100%);font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif;padding:env(safe-area-inset-top) 12px calc(18px + env(safe-area-inset-bottom));box-sizing:border-box}
.ge-top{max-width:760px;margin:auto;height:70px;display:grid;grid-template-columns:48px 1fr 48px;align-items:center;text-align:center}.ge-top b{font-size:18px;letter-spacing:.12em}.ge-top small{display:block;color:#7f94ab;font-size:10px;letter-spacing:.22em;margin-top:2px}.ge-back,.ge-restart{height:42px;border:1px solid #29435f;border-radius:14px;background:#10233a;color:#dceeff;font-size:28px}.ge-restart{font-size:22px}
.ge-score{max-width:740px;margin:4px auto 12px;display:grid;grid-template-columns:1fr 1.35fr 1fr;gap:8px}.ge-score>div{border:1px solid #263d56;background:rgba(12,28,47,.88);border-radius:15px;padding:9px 12px}.ge-score span,.ge-score small{font-size:10px;color:#91a5b8;display:block}.ge-score b{font-size:20px}.ge-score .blue{border-color:#237ac0}.ge-score .blue b{color:#4db6ff}.ge-score .red{text-align:right;border-color:#a53f47}.ge-score .red b{color:#ff6b70}.ge-score .turn{text-align:center}.ge-score .turn b{font-size:13px}.ge-score .turn small{margin-top:3px}
.ge-board-wrap{max-width:740px;margin:auto;border:1px solid #29435f;border-radius:22px;padding:7px;background:#07182a;box-shadow:0 20px 60px #0008;overflow:hidden}.ge-board{display:grid;grid-template-columns:repeat(10,minmax(0,1fr));gap:2px;aspect-ratio:10/8;background:radial-gradient(circle at 40% 30%,#164b6a,#08233b 70%);border-radius:16px;overflow:hidden}.ge-cell{position:relative;border:0;border-radius:4px;color:#fff;font-weight:900;font-size:13px;box-shadow:inset 0 0 0 1px #ffffff12;transition:transform .08s,filter .08s;touch-action:manipulation;-webkit-tap-highlight-color:transparent;user-select:none;padding:0}.ge-cell:active{transform:scale(.82);filter:brightness(1.6)}.ge-cell.water{pointer-events:none;background:linear-gradient(145deg,#0c3855,#0a2944);box-shadow:inset 0 0 12px #1e6e9133}.ge-cell.land.plain{background:linear-gradient(145deg,#658569,#465f4b)}.ge-cell.land.forest{background:linear-gradient(145deg,#315f46,#203f34)}.ge-cell.land.mountain{background:linear-gradient(145deg,#77776f,#4f514e)}.ge-cell.land.city{background:linear-gradient(145deg,#957a45,#615332)}.ge-cell.blue{background:linear-gradient(145deg,#2699e9,#155d9a)!important}.ge-cell.red{background:linear-gradient(145deg,#e3565e,#922c39)!important}.ge-cell.selected{outline:3px solid #fff;outline-offset:-3px;z-index:2;transform:scale(.9);filter:brightness(1.35);animation:geselect .75s infinite alternate}.ge-cell.target{filter:brightness(1.45);box-shadow:inset 0 0 0 3px #f7d45e}.ge-power{position:relative;z-index:2;display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;padding:0 3px;border-radius:8px;background:#07111dbb;text-shadow:0 1px 2px #000;font-size:12px}.ge-cell:before{position:absolute;left:3px;bottom:1px;font-size:9px;opacity:.65}.ge-cell.forest:before{content:'♣'}.ge-cell.mountain:before{content:'▲'}.ge-cell.city:before{content:'◆';color:#ffe38b}.ge-cell.capital:after{content:'★';position:absolute;top:1px;right:3px;font-size:10px;color:#ffe27a;text-shadow:0 1px 2px #000}.ge-cell.hit{animation:gehit .24s}.ge-cell.claim{animation:geclaim .35s}@keyframes geselect{to{box-shadow:inset 0 0 0 3px #fff,0 0 14px #fff9}}@keyframes gehit{50%{transform:scale(.72);filter:brightness(2)}}@keyframes geclaim{50%{transform:scale(1.18)}}
.ge-legend{max-width:720px;margin:10px auto 0;display:flex;justify-content:center;gap:14px;flex-wrap:wrap;color:#9cb0c2;font-size:10px}.ge-legend span{display:flex;align-items:center;gap:5px}.ge-legend i{display:block;width:10px;height:10px;border-radius:3px}.ge-legend i.blue{background:#268fd8}.ge-legend i.red{background:#d74c57}.ge-legend i.neutral{background:#58705c}
.ge-help{max-width:720px;margin:12px auto 0;background:#10233a;border:1px solid #263d56;border-radius:14px;padding:11px 14px;display:flex;gap:12px;align-items:center}.ge-help b{white-space:nowrap;font-size:12px;color:#f2c650}.ge-help span{font-size:11px;line-height:1.5;color:#9cb0c2}
.ge-modal{display:none;position:fixed;inset:0;background:#020711dd;z-index:99;align-items:center;justify-content:center;padding:24px}.ge-modal.show{display:flex}.ge-modal>div{text-align:center;background:#10233a;border:1px solid #3c5875;border-radius:24px;padding:34px;width:min(340px,90vw);box-shadow:0 30px 80px #000}.ge-modal b{display:block;font-size:30px}.ge-modal span{display:block;color:#9eb0c2;margin:8px 0 24px}.ge-modal button{border:0;border-radius:14px;background:#2b98e7;color:white;font-weight:800;padding:13px 28px}
@media(max-width:520px){.ge-app{padding-left:7px;padding-right:7px}.ge-board-wrap{padding:4px}.ge-board{gap:1px}.ge-score{grid-template-columns:1fr 1.25fr 1fr}.ge-help{align-items:flex-start}.ge-power{min-width:20px;height:20px;font-size:11px}}
</style>
'''


GAME_JS = r'''
<script>
setTimeout(()=>{
 const W=10,H=8,N=W*H,LAND=['0011111000','0111111110','1111111110','1111111111','0111111111','0111111110','0011111100','0001111000']; let cells=[],selected=-1,timer=null,aiTimer=null,ended=false;
 const board=document.getElementById('ge-board'), state=document.getElementById('ge-state'), hint=document.getElementById('ge-hint');
 const neighbors=i=>{const x=i%W,y=Math.floor(i/W),a=[];if(x)a.push(i-1);if(x<W-1)a.push(i+1);if(y)a.push(i-W);if(y<H-1)a.push(i+W);return a};
 function init(){clearInterval(timer);clearInterval(aiTimer);ended=false;selected=-1;cells=Array.from({length:N},(_,i)=>{const land=LAND[Math.floor(i/W)][i%W]==='1';const terrain=!land?'water':i%13===0?'city':i%7===0?'mountain':i%4===0?'forest':'plain';return{o:land?'n':'w',p:land?1+Math.floor(Math.random()*5):0,c:false,t:terrain}});
  Object.assign(cells[62],{o:'b',p:16,c:true});Object.assign(cells[52],{o:'b',p:7});Object.assign(cells[63],{o:'b',p:7});
  Object.assign(cells[18],{o:'r',p:16,c:true});Object.assign(cells[17],{o:'r',p:7});Object.assign(cells[28],{o:'r',p:7});
  render();state.textContent='戦闘開始';hint.textContent='青い領地を選択';
  timer=setInterval(grow,900);aiTimer=setInterval(ai,1050);
 }
 function render(anim=-1,klass=''){board.innerHTML='';let bc=0,rc=0;cells.forEach((c,i)=>{if(c.o==='b')bc++;if(c.o==='r')rc++;const b=document.createElement('button'),land=c.o!=='w',target=selected>=0&&land&&neighbors(selected).includes(i);b.className='ge-cell '+(land?'land '+c.t:'water')+(c.o==='b'?' blue':c.o==='r'?' red':'')+(c.c?' capital':'')+(i===selected?' selected':'')+(target?' target':'')+(i===anim?' '+klass:'');b.disabled=!land;b.setAttribute('aria-label',land?`兵力 ${c.p}`:'海');if(land){b.innerHTML='<span class="ge-power">'+c.p+'</span>';b.onpointerdown=e=>{e.preventDefault();tap(i)}}board.appendChild(b)});document.getElementById('ge-blue').textContent=bc;document.getElementById('ge-red').textContent=rc}
 function tap(i){if(ended||cells[i].o==='w')return;const c=cells[i];if(selected===i){selected=-1;state.textContent='選択解除';hint.textContent='青い領地を選択';render();return}if(selected>=0&&neighbors(selected).includes(i)){const from=selected,moving=c.o==='b';selected=-1;attack(from,i,'b');state.textContent=moving?'兵力を移動':'侵攻完了';hint.textContent='次の青い領地を選択';return}if(c.o==='b'){selected=i;state.textContent='兵力 '+c.p;hint.textContent='隣の領地へ侵攻・移動';render();return}}
 function attack(from,to,owner){const a=cells[from],d=cells[to];if(a.o!==owner||a.p<2)return;const force=Math.max(1,Math.floor(a.p*.65));a.p-=force;if(d.o===owner){d.p+=force;render(to,'claim');return}if(force>d.p){const wasCapital=d.c;d.o=owner;d.p=force-d.p;render(to,'claim');if(wasCapital)finish(owner)}else{d.p-=force;render(to,'hit')}}
 function grow(){if(ended)return;cells.forEach(c=>{if((c.o==='b'||c.o==='r')&&c.p<99)c.p+=c.c||c.t==='city'?2:1});render()}
 function ai(){if(ended)return;const frontier=[];cells.forEach((c,i)=>{if(c.o==='r'&&c.p>2){const opts=neighbors(i).filter(n=>cells[n].o!=='r'&&cells[n].o!=='w');if(opts.length)frontier.push([i,opts])}});if(!frontier.length)return;frontier.sort((a,b)=>cells[b[0]].p-cells[a[0]].p);const pick=frontier[Math.floor(Math.random()*Math.min(3,frontier.length))], targets=pick[1].sort((a,b)=>(cells[a].p+(cells[a].o==='b'?-3:0))-(cells[b].p+(cells[b].o==='b'?-3:0)));attack(pick[0],targets[0],'r')}
 function finish(winner){ended=true;clearInterval(timer);clearInterval(aiTimer);document.getElementById('ge-result').textContent=winner==='b'?'勝利！':'敗北…';document.getElementById('ge-result-sub').textContent=winner==='b'?'敵の首都を制圧しました':'自軍の首都が奪われました';document.getElementById('ge-modal').classList.add('show')}
 document.getElementById('ge-restart').onclick=init;document.getElementById('ge-again').onclick=()=>{document.getElementById('ge-modal').classList.remove('show');init()};init();
}, 150);
</script>
'''


@ui.page('/grid-empire')
def grid_empire_page():
    if not require_app_access('grid_empire'):
        return
    Theme.page('GRID EMPIRE', app_name='grid-empire')
    ui.add_head_html(GAME_CSS)
    ui.html(GAME_HTML, sanitize=False)
    ui.add_body_html(GAME_JS)
