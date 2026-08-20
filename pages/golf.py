from nicegui import ui

from core.auth import current_role, require_app_access
from core.theme import Theme


@ui.page("/golf")
def golf_page():
    if not require_app_access("golf"):
        return
    Theme.page("R-GOLF", app_name="golf")

    def action():
        if current_role() == "owner":
            ui.button(icon="apps", on_click=lambda: ui.navigate.to("/")).props(
                "flat round aria-label='R-BASEへ戻る'").classes("text-grey-8")

    content = Theme.shell("R-GOLF", "風を読み、指先でショット", action=action, brand="R-GOLF")
    with content:
        ui.html("""
        <div class="golf-stage">
          <div class="golf-hud">
            <div><small>HOLE</small><strong id="g-hole">1 / 3</strong></div>
            <div><small>PAR</small><strong id="g-par">3</strong></div>
            <div><small>SHOT</small><strong id="g-shot">0</strong></div>
            <div><small>WIND</small><strong id="g-wind">→ 2.1m</strong></div>
          </div>
          <canvas id="r-golf-canvas"></canvas>
          <div class="golf-guide" id="g-guide">ボールから後ろへ引っぱって、離すとショット！</div>
          <div class="golf-actions">
            <button id="g-reset">打ち直す</button><button id="g-next" hidden>次のホールへ</button>
          </div>
        </div>
        """, sanitize=False)
        ui.add_css("""
        body{background:linear-gradient(180deg,#EAF3F2,#F8F4E9)!important}.golf-stage{position:relative;width:100%;overflow:hidden;border-radius:28px;background:#A9D7DC;box-shadow:0 18px 45px rgba(19,55,62,.18)}.golf-hud{position:absolute;z-index:4;left:12px;right:12px;top:12px;display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.golf-hud div{display:flex;flex-direction:column;align-items:center;padding:7px 3px;border:1px solid rgba(255,255,255,.45);border-radius:13px;background:rgba(14,45,48,.72);color:#fff;backdrop-filter:blur(8px)}.golf-hud small{font-size:7px;letter-spacing:1.4px;opacity:.65}.golf-hud strong{font-size:11px;margin-top:1px}#r-golf-canvas{display:block;width:100%;height:min(67vh,610px);touch-action:none}.golf-guide{position:absolute;left:50%;bottom:62px;transform:translateX(-50%);width:max-content;max-width:85%;padding:8px 13px;border-radius:999px;background:rgba(255,255,255,.88);color:#29413D;font-size:10px;font-weight:800;text-align:center;box-shadow:0 5px 16px rgba(0,0,0,.12)}.golf-actions{position:absolute;z-index:5;left:14px;right:14px;bottom:14px;display:flex;gap:8px}.golf-actions button{flex:1;padding:10px;border:0;border-radius:14px;background:rgba(18,55,51,.88);color:#fff;font-size:11px;font-weight:900}.golf-actions #g-next{background:#D38A38}@media(min-width:700px){.app-shell{width:min(100%,1050px)!important}.golf-hud{left:20px;right:auto;width:440px}.golf-hud strong{font-size:14px}.golf-guide{font-size:12px}}
        """)
        ui.add_body_html("""
        <script>
        (() => {
          const start = () => {
            const c=document.getElementById('r-golf-canvas'); if(!c || c.dataset.ready) return;
            c.dataset.ready='1'; const x=c.getContext('2d');
            const holes=[{par:3,start:150,cup:870,wind:2.1,theme:0},{par:4,start:120,cup:940,wind:-1.4,theme:1},{par:4,start:120,cup:960,wind:3.2,theme:2}];
            let hi=0,shots=0,drag=false,aim=null,won=false,last=0;
            let ball={x:holes[0].start,y:0,vx:0,vy:0,moving:false};
            const W=1100,H=650, scale=()=>c.width/W;
            function terrain(px){const h=holes[hi];return 492+Math.sin((px+h.theme*95)/145)*24+Math.sin(px/61)*8+(px>500&&px<690?32*Math.sin((px-500)/190*Math.PI):0)}
            function resize(){const d=Math.min(devicePixelRatio||1,2),r=c.getBoundingClientRect();c.width=r.width*d;c.height=r.height*d;x.setTransform(c.width/W,0,0,c.height/H,0,0)}
            function reset(){const h=holes[hi];ball={x:h.start,y:terrain(h.start)-9,vx:0,vy:0,moving:false};aim=null;won=false;document.getElementById('g-next').hidden=true;document.getElementById('g-guide').textContent='ボールから後ろへ引っぱって、離すとショット！';hud()}
            function hud(){const h=holes[hi];document.getElementById('g-hole').textContent=`${hi+1} / 3`;document.getElementById('g-par').textContent=h.par;document.getElementById('g-shot').textContent=shots;document.getElementById('g-wind').textContent=`${h.wind>=0?'→':'←'} ${Math.abs(h.wind).toFixed(1)}m`}
            function cloud(cx,cy,s){x.fillStyle='rgba(255,255,255,.62)';[[0,0,35],[35,-8,46],[76,3,30]].forEach(a=>{x.beginPath();x.arc(cx+a[0]*s,cy+a[1]*s,a[2]*s,0,7);x.fill()})}
            function tree(tx,ty,s){x.fillStyle='#765339';x.fillRect(tx-6*s,ty-46*s,12*s,48*s);x.fillStyle='#386D55';[-24,0,23].forEach((v,i)=>{x.beginPath();x.arc(tx+v*s,ty-(50+(i%2)*15)*s,27*s,0,7);x.fill()})}
            function golfer(){if(ball.moving||won)return;const bx=ball.x-34,by=terrain(ball.x);x.strokeStyle='#26353A';x.lineWidth=6;x.lineCap='round';x.beginPath();x.moveTo(bx,by-80);x.lineTo(bx,by-38);x.lineTo(bx-15,by);x.moveTo(bx,by-38);x.lineTo(bx+17,by);x.moveTo(bx,by-68);x.lineTo(bx+22,by-45);x.stroke();x.fillStyle='#F0C7A4';x.beginPath();x.arc(bx,by-98,13,0,7);x.fill();x.fillStyle='#173D59';x.beginPath();x.arc(bx,by-103,15,3.1,6.3);x.fill();x.fillRect(bx-2,by-116,28,6);x.strokeStyle='#D8E2E2';x.lineWidth=4;x.beginPath();x.moveTo(bx+20,by-48);x.lineTo(bx+46,by-5);x.stroke();x.strokeStyle='#4B5B60';x.lineWidth=7;x.beginPath();x.moveTo(bx+41,by-7);x.lineTo(bx+54,by-5);x.stroke();x.fillStyle='#E16F4F';x.beginPath();x.moveTo(bx-11,by-82);x.lineTo(bx+11,by-82);x.lineTo(bx+8,by-45);x.lineTo(bx-9,by-45);x.closePath();x.fill()}
            function draw(){x.setTransform(c.width/W,0,0,c.height/H,0,0);const sky=x.createLinearGradient(0,0,0,H);sky.addColorStop(0,'#8ECAD5');sky.addColorStop(1,'#EAF0D2');x.fillStyle=sky;x.fillRect(0,0,W,H);cloud(130,145,.7);cloud(760,112,.85);x.fillStyle='#789F8B';x.beginPath();x.moveTo(0,410);for(let i=0;i<=W;i+=80)x.lineTo(i,300+Math.sin(i/150)*38);x.lineTo(W,520);x.lineTo(0,520);x.fill();for(let i=40;i<W;i+=135)tree(i,terrain(i)-4,.55+(i%3)*.08);x.fillStyle='#7DBD69';x.beginPath();x.moveTo(0,H);for(let i=0;i<=W;i+=8)x.lineTo(i,terrain(i));x.lineTo(W,H);x.fill();x.strokeStyle='#D7EAA8';x.lineWidth=10;x.beginPath();for(let i=0;i<=W;i+=8){const y=terrain(i);i?x.lineTo(i,y):x.moveTo(i,y)}x.stroke();const h=holes[hi];x.fillStyle='#D9C38A';x.beginPath();x.ellipse(610,terrain(610)+8,80,22,0,0,7);x.fill();x.strokeStyle='#F5F4EA';x.lineWidth=4;x.beginPath();x.moveTo(h.cup,terrain(h.cup));x.lineTo(h.cup,terrain(h.cup)-75);x.stroke();x.fillStyle='#E45A4D';x.beginPath();x.moveTo(h.cup,terrain(h.cup)-75);x.lineTo(h.cup+48,terrain(h.cup)-60);x.lineTo(h.cup,terrain(h.cup)-48);x.fill();x.fillStyle='#26343A';x.beginPath();x.ellipse(h.cup,terrain(h.cup)+1,10,4,0,0,7);x.fill();golfer();if(aim&&!ball.moving){x.strokeStyle='rgba(255,255,255,.9)';x.lineWidth=4;x.setLineDash([10,8]);x.beginPath();x.moveTo(ball.x,ball.y);x.lineTo(aim.x,aim.y);x.stroke();x.setLineDash([]);const p=Math.min(100,Math.hypot(aim.x-ball.x,aim.y-ball.y)/2);x.fillStyle='rgba(15,45,45,.65)';x.fillRect(ball.x-45,ball.y+22,90,8);x.fillStyle=p>75?'#ED7A51':'#F4D25F';x.fillRect(ball.x-45,ball.y+22,p*.9,8)}x.fillStyle='#fff';x.shadowColor='rgba(0,0,0,.25)';x.shadowBlur=7;x.beginPath();x.arc(ball.x,ball.y,9,0,7);x.fill();x.shadowBlur=0;requestAnimationFrame(draw)}
            function step(t){const dt=Math.min((t-last)/16.7,2);last=t;if(ball.moving){const h=holes[hi];ball.vx+=h.wind*.006*dt;ball.vy+=.31*dt;ball.x+=ball.vx*dt;ball.y+=ball.vy*dt;const gy=terrain(ball.x)-9;if(ball.y>=gy){ball.y=gy;ball.vy*=-.28;ball.vx*=.82;if(Math.abs(ball.vy)<.8)ball.vy=0;if(Math.abs(ball.vx)<.22){ball.moving=false;ball.vx=0}}if(ball.x<12||ball.x>W-12){ball.vx*=-.45;ball.x=Math.max(12,Math.min(W-12,ball.x))}if(!ball.moving&&Math.abs(ball.x-h.cup)<17){won=true;ball.x=h.cup;ball.y=terrain(h.cup)-2;document.getElementById('g-guide').textContent=shots<=h.par?'NICE PAR! 次のホールへ':'HOLE OUT! 次のホールへ';document.getElementById('g-next').hidden=false}}requestAnimationFrame(step)}
            function pos(e){const r=c.getBoundingClientRect(),p=e.touches?e.touches[0]:e;return{x:(p.clientX-r.left)/r.width*W,y:(p.clientY-r.top)/r.height*H}}
            c.addEventListener('pointerdown',e=>{if(ball.moving||won)return;drag=true;aim=pos(e);c.setPointerCapture(e.pointerId)});c.addEventListener('pointermove',e=>{if(drag)aim=pos(e)});c.addEventListener('pointerup',e=>{if(!drag)return;drag=false;const p=pos(e),dx=ball.x-p.x,dy=ball.y-p.y,d=Math.min(210,Math.hypot(dx,dy));if(d<24){aim=null;return}const k=d/Math.hypot(dx,dy);ball.vx=dx*k*.12;ball.vy=dy*k*.12;ball.moving=true;aim=null;shots++;hud()});
            document.getElementById('g-reset').onclick=()=>{shots=0;reset()};document.getElementById('g-next').onclick=()=>{hi=(hi+1)%holes.length;shots=0;reset()};window.addEventListener('resize',resize);resize();reset();requestAnimationFrame(draw);requestAnimationFrame(step)
          }; setTimeout(start,250);
        })();
        </script>
        """)
