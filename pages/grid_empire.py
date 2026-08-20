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
  <div class="ge-help"><b>遊び方</b><span>青いマスを選び、隣のマスをタップして侵攻。敵の★首都を奪えば勝利。</span></div>
  <div id="ge-modal" class="ge-modal"><div><b id="ge-result"></b><span id="ge-result-sub"></span><button id="ge-again">もう一度</button></div></div>
</div>
'''


GAME_CSS = r'''
<style>
body{margin:0;background:#081525!important;color:#fff;overscroll-behavior:none}.nicegui-content{padding:0!important}
.ge-app{min-height:100dvh;background:radial-gradient(circle at 50% 0,#163252 0,#081525 48%,#050b14 100%);font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif;padding:env(safe-area-inset-top) 12px calc(18px + env(safe-area-inset-bottom));box-sizing:border-box}
.ge-top{max-width:760px;margin:auto;height:70px;display:grid;grid-template-columns:48px 1fr 48px;align-items:center;text-align:center}.ge-top b{font-size:18px;letter-spacing:.12em}.ge-top small{display:block;color:#7f94ab;font-size:10px;letter-spacing:.22em;margin-top:2px}.ge-back,.ge-restart{height:42px;border:1px solid #29435f;border-radius:14px;background:#10233a;color:#dceeff;font-size:28px}.ge-restart{font-size:22px}
.ge-score{max-width:740px;margin:4px auto 12px;display:grid;grid-template-columns:1fr 1.35fr 1fr;gap:8px}.ge-score>div{border:1px solid #263d56;background:rgba(12,28,47,.88);border-radius:15px;padding:9px 12px}.ge-score span,.ge-score small{font-size:10px;color:#91a5b8;display:block}.ge-score b{font-size:20px}.ge-score .blue{border-color:#237ac0}.ge-score .blue b{color:#4db6ff}.ge-score .red{text-align:right;border-color:#a53f47}.ge-score .red b{color:#ff6b70}.ge-score .turn{text-align:center}.ge-score .turn b{font-size:13px}.ge-score .turn small{margin-top:3px}
.ge-board-wrap{max-width:740px;margin:auto;border:1px solid #29435f;border-radius:18px;padding:7px;background:rgba(3,10,19,.72);box-shadow:0 20px 60px #0008;overflow:auto}.ge-board{display:grid;grid-template-columns:repeat(12,minmax(38px,1fr));gap:3px;min-width:490px;aspect-ratio:12/8}.ge-cell{position:relative;border:0;border-radius:6px;background:#263544;color:#fff;font-weight:800;font-size:13px;box-shadow:inset 0 0 0 1px #ffffff0d;transition:transform .12s,filter .12s}.ge-cell.blue{background:linear-gradient(145deg,#2085ce,#135b9c)}.ge-cell.red{background:linear-gradient(145deg,#d64a53,#8e2935)}.ge-cell.selected{outline:3px solid #fff;z-index:2;transform:scale(.92)}.ge-cell.target{filter:brightness(1.35);box-shadow:inset 0 0 0 2px #f7d45e}.ge-cell.capital:after{content:'★';position:absolute;top:2px;right:3px;font-size:9px;color:#ffe27a}.ge-cell.hit{animation:gehit .24s}.ge-cell.claim{animation:geclaim .35s}@keyframes gehit{50%{transform:scale(.72);filter:brightness(2)}}@keyframes geclaim{50%{transform:scale(1.18)}}
.ge-help{max-width:720px;margin:12px auto 0;background:#10233a;border:1px solid #263d56;border-radius:14px;padding:11px 14px;display:flex;gap:12px;align-items:center}.ge-help b{white-space:nowrap;font-size:12px;color:#f2c650}.ge-help span{font-size:11px;line-height:1.5;color:#9cb0c2}
.ge-modal{display:none;position:fixed;inset:0;background:#020711dd;z-index:99;align-items:center;justify-content:center;padding:24px}.ge-modal.show{display:flex}.ge-modal>div{text-align:center;background:#10233a;border:1px solid #3c5875;border-radius:24px;padding:34px;width:min(340px,90vw);box-shadow:0 30px 80px #000}.ge-modal b{display:block;font-size:30px}.ge-modal span{display:block;color:#9eb0c2;margin:8px 0 24px}.ge-modal button{border:0;border-radius:14px;background:#2b98e7;color:white;font-weight:800;padding:13px 28px}
@media(max-width:520px){.ge-board-wrap{margin-left:-4px;margin-right:-4px}.ge-score{grid-template-columns:1fr 1.25fr 1fr}.ge-help{align-items:flex-start}}
</style>
'''


GAME_JS = r'''
<script>
setTimeout(()=>{
 const W=12,H=8,N=W*H; let cells=[],selected=-1,timer=null,aiTimer=null,ended=false;
 const board=document.getElementById('ge-board'), state=document.getElementById('ge-state'), hint=document.getElementById('ge-hint');
 const neighbors=i=>{const x=i%W,y=Math.floor(i/W),a=[];if(x)a.push(i-1);if(x<W-1)a.push(i+1);if(y)a.push(i-W);if(y<H-1)a.push(i+W);return a};
 function init(){clearInterval(timer);clearInterval(aiTimer);ended=false;selected=-1;cells=Array.from({length:N},()=>({o:'n',p:0,c:false}));
  cells[W*(H-1)+1]={o:'b',p:16,c:true};cells[W*(H-2)+1]={o:'b',p:7,c:false};cells[W*(H-1)+2]={o:'b',p:7,c:false};
  cells[W-2]={o:'r',p:16,c:true};cells[W+W-2]={o:'r',p:7,c:false};cells[W-3]={o:'r',p:7,c:false};
  for(let i=0;i<N;i++)if(cells[i].o==='n')cells[i].p=1+Math.floor(Math.random()*5);render();state.textContent='戦闘開始';hint.textContent='青いマスを選択';
  timer=setInterval(grow,900);aiTimer=setInterval(ai,1050);
 }
 function render(anim=-1,klass=''){board.innerHTML='';let bc=0,rc=0;cells.forEach((c,i)=>{if(c.o==='b')bc++;if(c.o==='r')rc++;const b=document.createElement('button');b.className='ge-cell '+(c.o==='b'?'blue':c.o==='r'?'red':'')+(c.c?' capital':'')+(i===selected?' selected':'')+(selected>=0&&neighbors(selected).includes(i)?' target':'')+(i===anim?' '+klass:'');b.textContent=c.p;b.onclick=()=>tap(i);board.appendChild(b)});document.getElementById('ge-blue').textContent=bc;document.getElementById('ge-red').textContent=rc}
 function tap(i){if(ended)return;const c=cells[i];if(c.o==='b'){selected=i;state.textContent='兵力 '+c.p;hint.textContent='隣のマスへ侵攻';render();return}if(selected<0||!neighbors(selected).includes(i))return;attack(selected,i,'b');selected=-1}
 function attack(from,to,owner){const a=cells[from],d=cells[to];if(a.o!==owner||a.p<2)return;const force=Math.max(1,Math.floor(a.p*.65));a.p-=force;if(d.o===owner){d.p+=force;render(to,'claim');return}if(force>d.p){const wasCapital=d.c;d.o=owner;d.p=force-d.p;render(to,'claim');if(wasCapital)finish(owner)}else{d.p-=force;render(to,'hit')}}
 function grow(){if(ended)return;cells.forEach(c=>{if(c.o!=='n'&&c.p<99)c.p+=c.c?2:1});render()}
 function ai(){if(ended)return;const frontier=[];cells.forEach((c,i)=>{if(c.o==='r'&&c.p>2){const opts=neighbors(i).filter(n=>cells[n].o!=='r');if(opts.length)frontier.push([i,opts])}});if(!frontier.length)return;frontier.sort((a,b)=>cells[b[0]].p-cells[a[0]].p);const pick=frontier[Math.floor(Math.random()*Math.min(3,frontier.length))], targets=pick[1].sort((a,b)=>(cells[a].p+(cells[a].o==='b'?-3:0))-(cells[b].p+(cells[b].o==='b'?-3:0)));attack(pick[0],targets[0],'r')}
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
