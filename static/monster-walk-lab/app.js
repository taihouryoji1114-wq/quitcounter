const ASSET='/static/digital-monsters/sprites/starters/';
const monsters={
  fire:{walk:'fire-walk-4x4-v5.png',thumb:'fire-starter-four-directions.png',columns:4},
  water:{walk:'water-walk-4x4-v4.png',thumb:'water-starter-four-directions.png',columns:4},
  nature:{walk:'nature-walk-3x4.png',thumb:'nature-starter-four-directions.png',columns:3},
  chankocchi:{walk:'chankocchi-walk-3x4.png',thumb:'chankocchi-four-directions.png',columns:3}
};
const room=document.querySelector('#room'),actor=document.querySelector('#actor'),sprite=document.querySelector('#sprite');
const spriteContext=sprite.getContext('2d');spriteContext.imageSmoothingEnabled=false;
const autoButton=document.querySelector('#auto'),state=document.querySelector('#state'),thought=document.querySelector('#thought');
let x=.50,y=.60,target={x:.5,y:.6},direction='down',auto=true,last=performance.now(),nextTarget=0,manual=null,walkFrame=-1,currentMonster='fire',currentChoice=monsters.fire,walkImage=null;
const directionRows={down:0,up:1,right:2,left:3};
function renderSprite(){
  if(!walkImage||!walkImage.complete||!walkImage.naturalWidth)return;
  const cellWidth=walkImage.naturalWidth/currentChoice.columns,cellHeight=walkImage.naturalHeight/4;
  const frame=Math.max(0,Math.min(currentChoice.columns-1,walkFrame));
  const mirrorLeftWalk=['fire','water'].includes(currentMonster)&&direction==='right';
  const sourceRow=mirrorLeftWalk?directionRows.left:directionRows[direction];
  spriteContext.clearRect(0,0,sprite.width,sprite.height);
  spriteContext.save();
  if(mirrorLeftWalk){spriteContext.translate(sprite.width,0);spriteContext.scale(-1,1)}
  spriteContext.drawImage(walkImage,frame*cellWidth,sourceRow*cellHeight,
    cellWidth,cellHeight,0,0,sprite.width,sprite.height);
  spriteContext.restore();
}
function setMonster(name){
  const choice=monsters[name]||monsters.fire;
  currentMonster=monsters[name]?name:'fire';
  currentChoice=choice;
  actor.classList.toggle('precise-cycle',['fire','water'].includes(currentMonster));
  walkImage=new Image();walkImage.decoding='async';walkImage.onload=()=>renderSprite();
  walkImage.src=`${ASSET}${choice.walk}`;
  document.querySelectorAll('.monster').forEach(b=>b.classList.toggle('active',b.dataset.monster===name));
  localStorage.setItem('walkLabMonster',name);
}
function face(dir){
  if(dir===direction)return;
  actor.classList.remove(`dir-${direction}`);
  direction=dir;
  actor.classList.add(`dir-${direction}`);
  renderSprite();
}
function chooseTarget(nx,ny){target.x=Math.max(.10,Math.min(.90,nx));target.y=Math.max(.35,Math.min(.86,ny));nextTarget=performance.now()+1800+Math.random()*2600}
function showThought(){
  if(actor.classList.contains('moving')||thought.classList.contains('show'))return;
  thought.textContent=['♪','…','!','♡'][Math.floor(Math.random()*4)];thought.style.left=`calc(${x*100}% + 28px)`;thought.style.top=`calc(${y*100}% - 74px)`;
  thought.classList.add('show');setTimeout(()=>thought.classList.remove('show'),1800);
}
function idleFrame(){return 1}
function tick(now){
  const dt=Math.min(.035,(now-last)/1000);last=now;
  if(manual){target.x=x+(manual==='left'?-.2:manual==='right'?.2:0);target.y=y+(manual==='up'?-.2:manual==='down'?.2:0)}
  else if(auto&&now>nextTarget)chooseTarget(.13+Math.random()*.74,.38+Math.random()*.44);
  let dx=target.x-x,dy=target.y-y,dist=Math.hypot(dx,dy),moving=dist>.006;
  if(moving){
    const speed=(manual?.29:.105)*dt;x+=dx/dist*Math.min(dist,speed);y+=dy/dist*Math.min(dist,speed);
    const dir=Math.abs(dx)>Math.abs(dy)?(dx>0?'right':'left'):(dy>0?'down':'up');face(dir);actor.classList.add('moving');
    const frames=currentChoice.columns===4?[0,1,2,3]:[0,1,2,1];
    const nextFrame=frames[Math.floor(now/130)%4];
    if(nextFrame!==walkFrame){walkFrame=nextFrame;renderSprite()}
    state.textContent=manual?'あなたと歩行中':'部屋を探検中';
  }else{actor.classList.remove('moving');const restingFrame=idleFrame();if(walkFrame!==restingFrame)walkFrame=restingFrame;renderSprite();state.textContent='ひと休み中';if(Math.random()<.003)showThought()}
  x=Math.max(.09,Math.min(.91,x));y=Math.max(.34,Math.min(.87,y));actor.style.left=`${x*100}%`;actor.style.top=`${y*100}%`;
  requestAnimationFrame(tick);
}
room.addEventListener('pointerdown',e=>{if(e.target.closest('button'))return;const r=room.getBoundingClientRect();auto=false;autoButton.classList.remove('active');autoButton.textContent='自動さんぽ OFF';chooseTarget((e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height)});
autoButton.addEventListener('click',()=>{auto=!auto;manual=null;autoButton.classList.toggle('active',auto);autoButton.textContent=`自動さんぽ ${auto?'ON':'OFF'}`;if(auto)chooseTarget(Math.random(),.5+Math.random()*.3)});
document.querySelectorAll('.monster').forEach(b=>{const url=`url('${ASSET}${monsters[b.dataset.monster].thumb}')`;b.style.setProperty('--thumb',url);b.addEventListener('click',()=>setMonster(b.dataset.monster))});
document.querySelectorAll('[data-lab]').forEach(button=>button.addEventListener('click',()=>{
  if(button.dataset.lab==='バトル'){startBattle();return}
  state.textContent=`${button.dataset.lab}研究を準備中`;
  thought.textContent={生成:'✦',お世話:'♡',部屋:'⌂',バトル:'⚔'}[button.dataset.lab];
  thought.style.left=`calc(${x*100}% + 28px)`;thought.style.top=`calc(${y*100}% - 74px)`;
  thought.classList.remove('show');void thought.offsetWidth;thought.classList.add('show');
}));
document.querySelectorAll('[data-dir]').forEach(b=>{const start=e=>{e.preventDefault();auto=false;autoButton.classList.remove('active');autoButton.textContent='自動さんぽ OFF';manual=b.dataset.dir;face(manual)};const end=()=>{manual=null;target={x,y}};b.addEventListener('pointerdown',start);b.addEventListener('pointerup',end);b.addEventListener('pointercancel',end);b.addEventListener('pointerleave',end)});
document.querySelector('#stop').addEventListener('click',()=>{auto=false;manual=null;target={x,y};autoButton.classList.remove('active');autoButton.textContent='自動さんぽ OFF'});

const battle=document.querySelector('#battle'),battleMessage=document.querySelector('#battle-message');
const battleCommand=document.querySelector('#battle-command'),battleMoves=document.querySelector('#battle-moves');
const playerHpBar=document.querySelector('#player-hp'),enemyHpBar=document.querySelector('#enemy-hp');
const playerHpText=document.querySelector('#player-hp-text');
const playerBattler=document.querySelector('#player-battler'),enemyBattler=document.querySelector('#enemy-battler');
let battleState={player:24,enemy:24,busy:false,guard:false,over:false};

function drawBattleSprite(canvas,file,column){
  const image=new Image();image.onload=()=>{
    const context=canvas.getContext('2d');context.imageSmoothingEnabled=false;
    context.clearRect(0,0,canvas.width,canvas.height);
    const width=image.naturalWidth/2,height=image.naturalHeight/2;
    context.drawImage(image,column*width,0,width,height,0,0,canvas.width,canvas.height);
  };image.src=`${ASSET}${file}`;
}
function updateBattleHp(){
  playerHpBar.style.width=`${Math.max(0,battleState.player)/24*100}%`;
  enemyHpBar.style.width=`${Math.max(0,battleState.enemy)/24*100}%`;
  playerHpText.textContent=Math.max(0,battleState.player);
  playerHpBar.classList.toggle('low',battleState.player<=7);enemyHpBar.classList.toggle('low',battleState.enemy<=7);
}
function showCommands(){battleCommand.hidden=false;battleMoves.hidden=true}
function showMoves(){if(battleState.busy||battleState.over)return;battleCommand.hidden=true;battleMoves.hidden=false;battleMessage.textContent='どの技を つかう？'}
function battleText(text,delay=720){battleMessage.textContent=text;return new Promise(resolve=>setTimeout(resolve,delay))}
function battleHit(target){target.classList.remove('hit');void target.offsetWidth;target.classList.add('hit')}
function battleAttack(target){target.classList.remove('attack');void target.offsetWidth;target.classList.add('attack')}
function damage(min,max){return min+Math.floor(Math.random()*(max-min+1))}

async function useMove(name){
  if(battleState.busy||battleState.over)return;battleState.busy=true;battleMoves.hidden=true;
  const moves={ember:['ひのこ',4,6],tackle:['たいあたり',3,5],tail:['しっぽアタック',4,5]};
  if(name==='guard'){
    battleState.guard=true;battleAttack(playerBattler);await battleText('イグニスは ほのおのまもりを まとった！');
  }else{
    const move=moves[name];battleAttack(playerBattler);await battleText(`イグニスの ${move[0]}！`,480);
    battleHit(enemyBattler);battleState.enemy-=damage(move[1],move[2]);updateBattleHp();await battleText('アクアロに ダメージ！');
  }
  if(battleState.enemy<=0){battleState.over=true;await battleText('アクアロは たおれた！');battleMessage.textContent='イグニスの かち！　画面をタップして再戦';battle.classList.add('battle-won');battleState.busy=false;return}
  const enemyMove=Math.random()<.68?['みずでっぽう',5,7]:['たいあたり',3,5];battleAttack(enemyBattler);await battleText(`アクアロの ${enemyMove[0]}！`,480);
  battleHit(playerBattler);let hit=damage(enemyMove[1],enemyMove[2]);if(battleState.guard){hit=Math.max(1,Math.floor(hit/2));battleState.guard=false}
  battleState.player-=hit;updateBattleHp();await battleText('イグニスに ダメージ！');
  if(battleState.player<=0){battleState.over=true;await battleText('イグニスは たおれた！');battleMessage.textContent='アクアロの かち！　画面をタップして再戦';battle.classList.add('battle-lost')}
  else{battleMessage.textContent='イグニスは どうする？';showCommands()}
  battleState.busy=false;
}
function startBattle(){
  auto=false;manual=null;target={x,y};battleState={player:24,enemy:24,busy:false,guard:false,over:false};
  battle.classList.remove('battle-won','battle-lost');battle.hidden=false;updateBattleHp();showCommands();
  battleMessage.textContent='アクアロが あらわれた！';
  drawBattleSprite(playerBattler,monsters.fire.thumb,1);drawBattleSprite(enemyBattler,monsters.water.thumb,0);
  setTimeout(()=>{if(!battleState.busy&&!battleState.over)battleMessage.textContent='イグニスは どうする？'},800);
}
function closeBattle(){battle.hidden=true}
document.querySelector('#battle-close').addEventListener('click',closeBattle);
document.querySelector('#move-back').addEventListener('click',()=>{battleMessage.textContent='イグニスは どうする？';showCommands()});
document.querySelectorAll('[data-move]').forEach(button=>button.addEventListener('click',()=>useMove(button.dataset.move)));
document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>{
  if(button.dataset.command==='fight'){showMoves();return}
  if(button.dataset.command==='run'){closeBattle();return}
  battleMessage.textContent=button.dataset.command==='party'?'交代できる仲間は まだいない！':'どうぐは まだ持っていない！';
}));
battleMessage.addEventListener('click',()=>{if(battleState.over)startBattle()});
const requestedMonster=new URLSearchParams(location.search).get('monster');
setMonster(monsters[requestedMonster]?requestedMonster:(localStorage.getItem('walkLabMonster')||'fire'));
chooseTarget(.25,.7);requestAnimationFrame(tick);
