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
            <div><small>CLUB</small><strong id="g-club">IRON</strong></div>
            <div><small>WIND</small><strong id="g-wind">→ 2.1m</strong></div>
          </div>
          <canvas id="r-golf-canvas"></canvas>
          <div class="golf-guide" id="g-guide">角度を選んで、ゲージのタイミングでショット！</div>
          <div class="golf-controls" id="g-controls">
            <div class="angle-control"><button id="g-angle-down">−</button><span>角度 <strong id="g-angle">45°</strong></span><button id="g-angle-up">＋</button></div>
            <div class="power-meter"><i class="nice-zone"></i><b id="g-power"></b></div>
            <button class="shot-button" id="g-swing">ショット！</button>
          </div>
          <div class="golf-actions">
            <button id="g-reset">打ち直す</button><button id="g-next" hidden>次のホールへ</button>
          </div>
        </div>
        """, sanitize=False)
        ui.add_css("""
        body{background:linear-gradient(180deg,#EAF3F2,#F8F4E9)!important}.golf-stage{position:relative;width:100%;overflow:hidden;border-radius:24px;background:#A9D7DC;box-shadow:0 18px 45px rgba(19,55,62,.18)}.golf-hud{position:absolute;z-index:4;left:8px;right:8px;top:8px;display:grid;grid-template-columns:repeat(5,1fr);gap:4px}.golf-hud div{display:flex;flex-direction:column;align-items:center;padding:6px 2px;border:1px solid rgba(255,255,255,.45);border-radius:10px;background:rgba(14,45,48,.72);color:#fff;backdrop-filter:blur(8px)}.golf-hud small{font-size:6px;letter-spacing:1px;opacity:.65}.golf-hud strong{font-size:10px;margin-top:1px}#r-golf-canvas{display:block;width:100%;height:calc(100dvh - 150px);min-height:610px;touch-action:none}.golf-guide{position:absolute;left:50%;bottom:170px;transform:translateX(-50%);width:max-content;max-width:90%;padding:7px 12px;border-radius:999px;background:rgba(255,255,255,.9);color:#29413D;font-size:9px;font-weight:800;text-align:center;box-shadow:0 5px 16px rgba(0,0,0,.12)}.golf-controls{position:absolute;z-index:5;left:10px;right:10px;bottom:51px;padding:8px;border-radius:17px;background:rgba(12,39,40,.86);backdrop-filter:blur(10px)}.angle-control{display:grid;grid-template-columns:42px 1fr 42px;align-items:center;gap:5px;color:#fff;text-align:center;font-size:10px}.angle-control button,.shot-button{border:0;border-radius:11px;background:#fff;color:#21443F;font-weight:900}.angle-control button{height:32px;font-size:20px}.power-meter{position:relative;height:13px;margin:7px 2px;border-radius:999px;overflow:hidden;background:linear-gradient(90deg,#65A8D1,#F3CE56 65%,#E76F50)}.power-meter .nice-zone{position:absolute;left:72%;width:14%;height:100%;background:rgba(255,255,255,.72);border-left:2px solid #fff;border-right:2px solid #fff}.power-meter b{position:absolute;top:-3px;left:0;width:6px;height:19px;border-radius:4px;background:#fff;box-shadow:0 0 7px rgba(0,0,0,.4)}.shot-button{width:100%;height:35px;background:#ECA746;color:#fff;font-size:12px}.golf-actions{position:absolute;z-index:6;left:10px;right:10px;bottom:9px;display:flex;gap:8px}.golf-actions button{flex:1;padding:8px;border:0;border-radius:12px;background:rgba(18,55,51,.9);color:#fff;font-size:10px;font-weight:900}.golf-actions #g-next{background:#D38A38}@media(max-width:699px){.app-shell{width:100%!important;padding:6px 5px 12px!important}.app-shell>.q-card:first-child{margin-bottom:5px!important}.golf-stage{border-radius:18px}}@media(min-width:700px){.app-shell{width:min(100%,1200px)!important}.golf-hud{left:20px;right:auto;width:540px}.golf-hud strong{font-size:13px}.golf-guide{font-size:11px}.golf-controls{left:50%;right:auto;transform:translateX(-50%);width:480px}}
        """)
        ui.add_body_html("""
        <script>
        (() => {
          const start = () => {
            const c=document.getElementById('r-golf-canvas'); if(!c || c.dataset.ready) return;
            c.dataset.ready='1'; const x=c.getContext('2d');
            const holes=[{par:3,start:150,cup:870,wind:2.1,theme:0},{par:4,start:120,cup:940,wind:-1.4,theme:1},{par:4,start:120,cup:960,wind:3.2,theme:2}];
            let hi=0,shots=0,won=false,last=0,angle=45,power=0,powerDir=1;
            let ball={x:holes[0].start,y:0,vx:0,vy:0,moving:false};
            const W=1100,H=650, scale=()=>c.width/W;
            function terrain(px){const h=holes[hi];return 492+Math.sin((px+h.theme*95)/145)*24+Math.sin(px/61)*8+(px>500&&px<690?32*Math.sin((px-500)/190*Math.PI):0)}
            function resize(){const d=Math.min(devicePixelRatio||1,2),r=c.getBoundingClientRect();c.width=r.width*d;c.height=r.height*d;x.setTransform(c.width/W,0,0,c.height/H,0,0)}
            function putting(){return !ball.moving&&Math.abs(ball.x-holes[hi].cup)<190}
            function reset(){const h=holes[hi];ball={x:h.start,y:terrain(h.start)-9,vx:0,vy:0,moving:false};won=false;angle=45;power=0;powerDir=1;document.getElementById('g-next').hidden=true;document.getElementById('g-guide').textContent='角度を選んで、ゲージのタイミングでショット！';hud()}
            function hud(){const h=holes[hi],putt=putting();document.getElementById('g-hole').textContent=`${hi+1} / 3`;document.getElementById('g-par').textContent=h.par;document.getElementById('g-shot').textContent=shots;document.getElementById('g-wind').textContent=`${h.wind>=0?'→':'←'} ${Math.abs(h.wind).toFixed(1)}m`;document.getElementById('g-club').textContent=putt?'PUTTER':'IRON';document.getElementById('g-angle').textContent=putt?'自動':`${angle}°`;document.getElementById('g-angle-down').disabled=putt;document.getElementById('g-angle-up').disabled=putt}
            function cloud(cx,cy,s){x.fillStyle='rgba(255,255,255,.62)';[[0,0,35],[35,-8,46],[76,3,30]].forEach(a=>{x.beginPath();x.arc(cx+a[0]*s,cy+a[1]*s,a[2]*s,0,7);x.fill()})}
            function tree(tx,ty,s){x.fillStyle='#765339';x.fillRect(tx-6*s,ty-46*s,12*s,48*s);x.fillStyle='#386D55';[-24,0,23].forEach((v,i)=>{x.beginPath();x.arc(tx+v*s,ty-(50+(i%2)*15)*s,27*s,0,7);x.fill()})}
            function golfer(){if(ball.moving||won)return;const bx=ball.x-34,by=terrain(ball.x);x.strokeStyle='#26353A';x.lineWidth=6;x.lineCap='round';x.beginPath();x.moveTo(bx,by-80);x.lineTo(bx,by-38);x.lineTo(bx-15,by);x.moveTo(bx,by-38);x.lineTo(bx+17,by);x.moveTo(bx,by-68);x.lineTo(bx+22,by-45);x.stroke();x.fillStyle='#F0C7A4';x.beginPath();x.arc(bx,by-98,13,0,7);x.fill();x.fillStyle='#173D59';x.beginPath();x.arc(bx,by-103,15,3.1,6.3);x.fill();x.fillRect(bx-2,by-116,28,6);x.strokeStyle='#D8E2E2';x.lineWidth=4;x.beginPath();x.moveTo(bx+20,by-48);x.lineTo(bx+46,by-5);x.stroke();x.strokeStyle='#4B5B60';x.lineWidth=7;x.beginPath();x.moveTo(bx+41,by-7);x.lineTo(bx+54,by-5);x.stroke();x.fillStyle='#E16F4F';x.beginPath();x.moveTo(bx-11,by-82);x.lineTo(bx+11,by-82);x.lineTo(bx+8,by-45);x.lineTo(bx-9,by-45);x.closePath();x.fill()}
            function draw(){x.setTransform(c.width/W,0,0,c.height/H,0,0);const sky=x.createLinearGradient(0,0,0,H);sky.addColorStop(0,'#8ECAD5');sky.addColorStop(1,'#EAF0D2');x.fillStyle=sky;x.fillRect(0,0,W,H);cloud(130,145,.7);cloud(760,112,.85);x.fillStyle='#789F8B';x.beginPath();x.moveTo(0,410);for(let i=0;i<=W;i+=80)x.lineTo(i,300+Math.sin(i/150)*38);x.lineTo(W,520);x.lineTo(0,520);x.fill();for(let i=40;i<W;i+=135)tree(i,terrain(i)-4,.55+(i%3)*.08);x.fillStyle='#7DBD69';x.beginPath();x.moveTo(0,H);for(let i=0;i<=W;i+=8)x.lineTo(i,terrain(i));x.lineTo(W,H);x.fill();x.strokeStyle='#D7EAA8';x.lineWidth=10;x.beginPath();for(let i=0;i<=W;i+=8){const y=terrain(i);i?x.lineTo(i,y):x.moveTo(i,y)}x.stroke();const h=holes[hi];x.fillStyle='#58A964';x.beginPath();x.ellipse(h.cup,terrain(h.cup)+5,150,25,0,0,7);x.fill();x.fillStyle='#D9C38A';x.beginPath();x.ellipse(610,terrain(610)+8,80,22,0,0,7);x.fill();x.strokeStyle='#F5F4EA';x.lineWidth=4;x.beginPath();x.moveTo(h.cup,terrain(h.cup));x.lineTo(h.cup,terrain(h.cup)-75);x.stroke();x.fillStyle='#E45A4D';x.beginPath();x.moveTo(h.cup,terrain(h.cup)-75);x.lineTo(h.cup+48,terrain(h.cup)-60);x.lineTo(h.cup,terrain(h.cup)-48);x.fill();x.fillStyle='#26343A';x.beginPath();x.ellipse(h.cup,terrain(h.cup)+1,10,4,0,0,7);x.fill();golfer();if(!ball.moving&&!won&&!putting()){const rad=angle*Math.PI/180;x.strokeStyle='rgba(255,255,255,.82)';x.lineWidth=3;x.setLineDash([9,8]);x.beginPath();x.moveTo(ball.x,ball.y);x.lineTo(ball.x+Math.cos(rad)*105,ball.y-Math.sin(rad)*105);x.stroke();x.setLineDash([])}x.fillStyle='#fff';x.shadowColor='rgba(0,0,0,.25)';x.shadowBlur=7;x.beginPath();x.arc(ball.x,ball.y,9,0,7);x.fill();x.shadowBlur=0;requestAnimationFrame(draw)}
            function step(t){const dt=Math.min((t-last)/16.7,2);last=t;if(!ball.moving&&!won){power+=powerDir*1.6*dt;if(power>=100){power=100;powerDir=-1}if(power<=0){power=0;powerDir=1}document.getElementById('g-power').style.left=`calc(${power}% - 3px)`}if(ball.moving){const h=holes[hi];ball.vx+=h.wind*.006*dt;ball.vy+=.31*dt;ball.x+=ball.vx*dt;ball.y+=ball.vy*dt;const gy=terrain(ball.x)-9;if(ball.y>=gy){ball.y=gy;ball.vy*=-.22;ball.vx*=.86;if(Math.abs(ball.vy)<.65)ball.vy=0;if(Math.abs(ball.vx)<.2){ball.moving=false;ball.vx=0;hud();document.getElementById('g-guide').textContent=putting()?'グリーンオン！ パターは強さだけで勝負':'角度を選んで次のショット'}}if(ball.x<12||ball.x>W-12){ball.vx*=-.45;ball.x=Math.max(12,Math.min(W-12,ball.x))}if(!ball.moving&&Math.abs(ball.x-h.cup)<17){won=true;ball.x=h.cup;ball.y=terrain(h.cup)-2;document.getElementById('g-guide').textContent=shots<=h.par?'NICE PAR! 次のホールへ':'HOLE OUT! 次のホールへ';document.getElementById('g-next').hidden=false}}requestAnimationFrame(step)}
            function swing(){if(ball.moving||won)return;const putt=putting(),nice=power>=72&&power<=86;if(putt){ball.vx=2+power*.075;ball.vy=-.35}else{const rad=angle*Math.PI/180,speed=5+power*.14;ball.vx=Math.cos(rad)*speed;ball.vy=-Math.sin(rad)*speed}ball.moving=true;shots++;document.getElementById('g-guide').textContent=nice?'ナイスショット！':power>90?'強いショット！':'ショット！';hud()}
            document.getElementById('g-angle-down').onclick=()=>{if(!putting()){angle=Math.max(15,angle-5);hud()}};document.getElementById('g-angle-up').onclick=()=>{if(!putting()){angle=Math.min(75,angle+5);hud()}};document.getElementById('g-swing').onclick=swing;document.getElementById('g-reset').onclick=()=>{shots=0;reset()};document.getElementById('g-next').onclick=()=>{hi=(hi+1)%holes.length;shots=0;reset()};window.addEventListener('resize',resize);resize();reset();requestAnimationFrame(draw);requestAnimationFrame(step)
          }; setTimeout(start,250);
        })();
        </script>
        """)
