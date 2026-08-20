from nicegui import ui

from core.auth import current_role, require_app_access
from core.theme import Theme


@ui.page("/stick-blade")
def stick_blade_page():
    if not require_app_access("stick_blade"):
        return
    Theme.page("STICK BLADE", app_name="stick-blade")

    def action():
        if current_role() == "owner":
            ui.button(icon="apps", on_click=lambda: ui.navigate.to("/")).props(
                "flat round aria-label='R-BASEへ戻る'").classes("text-grey-8")

    content = Theme.shell("STICK BLADE", "剣を取り、敵陣を突破せよ", action=action,
                          brand="STICK BLADE")
    with content:
        ui.html("""
        <div class="blade-game">
          <div class="blade-hud">
            <div class="blade-health"><i id="blade-hp"></i></div>
            <strong id="blade-status">STAGE 1</strong>
            <span id="blade-count">敵 6</span>
          </div>
          <canvas id="blade-canvas"></canvas>
          <div class="blade-message" id="blade-message">右へ進み、敵を倒せ！</div>
          <div class="blade-controls">
            <div><button id="blade-left">◀</button><button id="blade-right">▶</button></div>
            <button id="blade-jump">JUMP</button><button class="blade-attack" id="blade-attack">ATTACK</button>
          </div>
          <button class="blade-retry" id="blade-retry" hidden>もう一度挑戦</button>
        </div>
        """, sanitize=False)
        ui.add_css("""
        body{background:linear-gradient(180deg,#171523,#2C2531)!important;color:#fff}.app-shell{width:min(100%,1200px)!important}.app-shell>.text-grey-7{color:#BEB7C6!important}.blade-game{position:relative;width:100%;height:680px;overflow:hidden;border-radius:25px;background:#2B3342;box-shadow:0 20px 55px rgba(0,0,0,.38);user-select:none}.blade-hud{position:absolute;z-index:5;left:12px;right:12px;top:12px;display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:15px;background:rgba(16,15,24,.78);backdrop-filter:blur(8px)}.blade-health{flex:1;height:12px;border-radius:99px;background:#3B3543;overflow:hidden}.blade-health i{display:block;width:100%;height:100%;background:linear-gradient(90deg,#D34752,#F17A62)}.blade-hud strong{font-size:10px;letter-spacing:1px}.blade-hud span{font-size:9px;color:#D9D0DD}#blade-canvas{display:block;width:100%;height:100%;touch-action:none}.blade-message{position:absolute;z-index:4;left:50%;top:68px;transform:translateX(-50%);width:max-content;max-width:86%;padding:7px 13px;border:1px solid rgba(255,255,255,.2);border-radius:99px;background:rgba(25,22,33,.68);font-size:10px;font-weight:900;text-align:center}.blade-controls{position:absolute;z-index:6;left:10px;right:10px;bottom:10px;display:grid;grid-template-columns:1fr 76px 98px;gap:8px}.blade-controls>div{display:grid;grid-template-columns:1fr 1fr;gap:6px}.blade-controls button,.blade-retry{height:52px;border:1px solid rgba(255,255,255,.24);border-radius:15px;background:rgba(28,25,38,.84);color:#fff;font-weight:900;box-shadow:0 7px 17px rgba(0,0,0,.2)}.blade-controls .blade-attack{background:linear-gradient(145deg,#B73D4D,#E0644C)}.blade-retry{position:absolute;z-index:8;left:50%;top:55%;transform:translate(-50%,-50%);width:210px;background:#D64D51}@media(max-width:699px){.app-shell{padding:8px 5px 14px!important}.blade-game{height:calc(100dvh - 150px);min-height:590px;border-radius:18px}.blade-controls{grid-template-columns:1fr 68px 88px}.blade-controls button{height:58px;font-size:11px}}
        """)
        ui.add_body_html("""
        <script>
        (()=>{setTimeout(()=>{
          const c=document.getElementById('blade-canvas');if(!c||c.dataset.ready)return;c.dataset.ready='1';
          const g=c.getContext('2d'),W=1000,H=600,WORLD=3600,ground=485,keys={},touch={left:false,right:false};
          let last=0,camera=0,ended=false,attackTimer=0,invincible=0;
          const player={x:120,y:ground,vx:0,vy:0,hp:100,onGround:true,facing:1};
          let enemies=[];
          function spawn(){enemies=[620,1080,1510,1900,2360].map((x,i)=>({x,y:ground,hp:2,dead:false,hit:0,boss:false,color:i%2?'#765AA7':'#A44E55'}));enemies.push({x:3200,y:ground,hp:10,dead:false,hit:0,boss:true,color:'#742E45'});player.x=120;player.y=ground;player.vx=player.vy=0;player.hp=100;ended=false;attackTimer=0;document.getElementById('blade-retry').hidden=true;message('右へ進み、敵を倒せ！');hud()}
          function resize(){const d=Math.min(devicePixelRatio||1,2),r=c.getBoundingClientRect();c.width=r.width*d;c.height=r.height*d}
          function message(t){document.getElementById('blade-message').textContent=t}
          function hud(){document.getElementById('blade-hp').style.width=Math.max(0,player.hp)+'%';const alive=enemies.filter(e=>!e.dead);document.getElementById('blade-count').textContent='敵 '+alive.length;document.getElementById('blade-status').textContent=alive.some(e=>e.boss)?'STAGE 1':'CLEAR'}
          function mountains(offset,color,base,amp){g.fillStyle=color;g.beginPath();g.moveTo(0,H);for(let sx=0;sx<=W;sx+=70){const wx=sx+camera*offset;g.lineTo(sx,base+Math.sin(wx/170)*amp+Math.sin(wx/67)*amp*.25)}g.lineTo(W,H);g.fill()}
          function stick(x,y,scale,color,boss,attack,face=1){g.save();g.translate(x-camera,y);g.scale(face*scale,scale);g.lineCap='round';g.strokeStyle='#171821';g.lineWidth=7;g.beginPath();g.moveTo(0,-74);g.lineTo(0,-35);g.lineTo(-17,0);g.moveTo(0,-35);g.lineTo(18,0);g.moveTo(0,-62);g.lineTo(attack?42:24,attack?-45:-28);g.stroke();g.fillStyle='#D7A47E';g.beginPath();g.arc(0,-92,15,0,7);g.fill();g.fillStyle=color;g.beginPath();g.moveTo(-15,-76);g.lineTo(16,-76);g.lineTo(12,-38);g.lineTo(-12,-38);g.closePath();g.fill();g.fillStyle=boss?'#352033':'#263744';g.beginPath();g.arc(0,-98,17,3.05,6.3);g.fill();if(boss){g.fillStyle='#C7A64B';g.fillRect(-18,-116,36,7)}g.strokeStyle='#E9EBEC';g.lineWidth=4;g.beginPath();g.moveTo(attack?38:23,attack?-44:-29);g.lineTo(attack?82:51,attack?-45:-3);g.stroke();g.strokeStyle='#8D6646';g.lineWidth=7;g.beginPath();g.moveTo(attack?31:18,attack?-44:-28);g.lineTo(attack?43:29,attack?-44:-22);g.stroke();g.restore()}
          function draw(){const sx=c.width/W,sy=c.height/H;g.setTransform(sx,0,0,sy,0,0);const sky=g.createLinearGradient(0,0,0,H);sky.addColorStop(0,'#24283A');sky.addColorStop(1,'#805A60');g.fillStyle=sky;g.fillRect(0,0,W,H);g.fillStyle='rgba(244,225,181,.8)';g.beginPath();g.arc(820-camera*.03,100,42,0,7);g.fill();mountains(.12,'#353849',300,70);mountains(.28,'#454653',365,55);for(let wx=Math.floor(camera/180)*180-180;wx<camera+W+180;wx+=180){const sx=wx-camera;g.fillStyle='#252B31';g.fillRect(sx-6,ground-95,12,95);g.fillStyle='#303B39';g.beginPath();g.arc(sx,ground-115,42,0,7);g.fill()}g.fillStyle='#303A35';g.fillRect(0,ground,W,H-ground);g.fillStyle='#68755D';g.fillRect(0,ground-8,W,9);for(let wx=300;wx<WORLD;wx+=480){const sx=wx-camera;g.fillStyle='#514A51';g.fillRect(sx,ground-55,58,55);g.fillStyle='#6D6162';g.beginPath();g.moveTo(sx-8,ground-55);g.lineTo(sx+29,ground-88);g.lineTo(sx+66,ground-55);g.fill()}enemies.filter(e=>!e.dead&&Math.abs(e.x-camera-W/2)<W).forEach(e=>{stick(e.x,e.y,e.boss?1.42:1,e.hit>0?'#F4A05B':e.color,e.boss,e.hit>0,-1);if(e.boss){g.fillStyle='#231B26';g.fillRect(e.x-camera-65,e.y-145,130,8);g.fillStyle='#D24D58';g.fillRect(e.x-camera-65,e.y-145,130*(e.hp/10),8)}});stick(player.x,player.y,1,'#3B86A5',false,attackTimer>0,player.facing);requestAnimationFrame(draw)}
          function attack(){if(ended||attackTimer>0)return;attackTimer=13;let hit=false;enemies.forEach(e=>{if(e.dead)return;const dx=e.x-player.x;if(Math.sign(dx||1)===player.facing&&Math.abs(dx)<(e.boss?120:92)&&Math.abs(e.y-player.y)<70){e.hp--;e.hit=8;hit=true;if(e.hp<=0){e.dead=true;message(e.boss?'ボス撃破！ ステージクリア！':'敵を倒した！')}}});if(!hit)message('剣が空を切った');hud();if(enemies.every(e=>e.dead)){ended=true;document.getElementById('blade-retry').hidden=false}}
          function jump(){if(player.onGround&&!ended){player.vy=-12;player.onGround=false}}
          function step(t){const dt=Math.min((t-last)/16.7,2);last=t;if(!ended){const dir=(keys.ArrowLeft||keys.a||touch.left?-1:0)+(keys.ArrowRight||keys.d||touch.right?1:0);player.vx=dir*5.2;if(dir)player.facing=dir;player.x=Math.max(30,Math.min(WORLD-50,player.x+player.vx*dt));player.vy+=.62*dt;player.y+=player.vy*dt;if(player.y>=ground){player.y=ground;player.vy=0;player.onGround=true}if(attackTimer>0)attackTimer-=dt;if(invincible>0)invincible-=dt;enemies.forEach(e=>{if(e.dead)return;e.hit=Math.max(0,e.hit-dt);const dist=player.x-e.x;if(Math.abs(dist)<420)e.x+=Math.sign(dist)*(.75+(e.boss?.35:0))*dt;if(Math.abs(player.x-e.x)<(e.boss?70:45)&&Math.abs(player.y-e.y)<70&&invincible<=0){player.hp-=e.boss?18:10;invincible=45;player.x-=player.facing*45;message('ダメージ！ 距離を取れ');hud();if(player.hp<=0){ended=true;message('GAME OVER');document.getElementById('blade-retry').hidden=false}}});camera=Math.max(0,Math.min(WORLD-W,player.x-260))}requestAnimationFrame(step)}
          function hold(id,key){const b=document.getElementById(id);b.onpointerdown=e=>{e.preventDefault();touch[key]=true};['pointerup','pointercancel','pointerleave'].forEach(n=>b.addEventListener(n,()=>touch[key]=false))}
          hold('blade-left','left');hold('blade-right','right');document.getElementById('blade-jump').onclick=jump;document.getElementById('blade-attack').onclick=attack;document.getElementById('blade-retry').onclick=spawn;addEventListener('keydown',e=>{keys[e.key]=true;if(e.key===' ')attack();if(e.key==='ArrowUp'||e.key==='w')jump()});addEventListener('keyup',e=>keys[e.key]=false);addEventListener('resize',resize);resize();spawn();requestAnimationFrame(draw);requestAnimationFrame(step)
        },250)})();
        </script>
        """)
