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
const playerHpText=document.querySelector('#player-hp-text'),playerHpMax=document.querySelector('#player-hp-max');
const playerLevel=document.querySelector('#player-level'),playerXpBar=document.querySelector('#player-xp');
const playerBattler=document.querySelector('#player-battler'),enemyBattler=document.querySelector('#enemy-battler');
const moveLearn=document.querySelector('#move-learn'),moveBack=document.querySelector('#move-back');
const TYPE_CHART={fire:{nature:2,water:.5},water:{fire:2,nature:.5},nature:{water:2,fire:.5}};
const MOVE_DATA={
  ember:{name:'ひのこ',type:'fire',power:[4,6]},tackle:{name:'たいあたり',type:'normal',power:[3,5]},
  tail:{name:'しっぽアタック',type:'normal',power:[4,5]},guard:{name:'ほのおのまもり',type:'fire',guard:true},
  fireFang:{name:'ほのおのキバ',type:'fire',power:[6,8]},flameWheel:{name:'かえんぐるま',type:'fire',power:[7,9]},
};
const TYPE_NAME={fire:'ほのお',water:'みず',nature:'みどり',normal:'ノーマル'};
const LEARN_LEVELS={6:'fireFang',8:'flameWheel'};
function loadProfile(){
  try{
    const saved=JSON.parse(localStorage.getItem('laboIgnisProfile')||'{}');
    return {level:Math.max(5,Number(saved.level)||5),xp:Math.max(0,Number(saved.xp)||0),stage:Math.max(1,Number(saved.stage)||1),moves:Array.isArray(saved.moves)&&saved.moves.length?saved.moves.slice(0,4):['ember','tackle','tail','guard'],pendingMove:saved.pendingMove||null};
  }catch(_){return {level:5,xp:0,stage:1,moves:['ember','tackle','tail','guard'],pendingMove:null}}
}
let profile=loadProfile(),battleState={player:24,playerMax:24,enemy:24,busy:false,guard:false,over:false};
function saveProfile(){localStorage.setItem('laboIgnisProfile',JSON.stringify(profile))}
function xpNeeded(){return profile.level*12}
function typeMultiplier(attackType,defenderType){return TYPE_CHART[attackType]?.[defenderType]||1}

function drawBattleSprite(canvas,file,column){
  const image=new Image();image.onload=()=>{
    const context=canvas.getContext('2d');context.imageSmoothingEnabled=false;
    context.clearRect(0,0,canvas.width,canvas.height);
    const width=image.naturalWidth/2,height=image.naturalHeight/2;
    context.drawImage(image,column*width,0,width,height,0,0,canvas.width,canvas.height);
  };image.src=`${ASSET}${file}`;
}
function updateBattleHp(){
  playerHpBar.style.width=`${Math.max(0,battleState.player)/battleState.playerMax*100}%`;
  enemyHpBar.style.width=`${Math.max(0,battleState.enemy)/24*100}%`;
  playerHpText.textContent=Math.max(0,battleState.player);
  playerHpMax.textContent=battleState.playerMax;playerLevel.textContent=`Lv.${profile.level}　火`;
  playerXpBar.style.width=`${Math.min(100,profile.xp/xpNeeded()*100)}%`;
  playerHpBar.classList.toggle('low',battleState.player<=battleState.playerMax*.3);enemyHpBar.classList.toggle('low',battleState.enemy<=7);
}
function renderMoves(){
  battleMoves.querySelectorAll('[data-move]').forEach(button=>button.remove());
  profile.moves.forEach(id=>{const move=MOVE_DATA[id];if(!move)return;const button=document.createElement('button');button.type='button';button.dataset.move=id;button.innerHTML=`<b>${move.name}</b><small>${TYPE_NAME[move.type]}</small>`;button.addEventListener('click',()=>useMove(id));battleMoves.insertBefore(button,moveBack)});
}
function showCommands(){battleCommand.hidden=false;battleMoves.hidden=true;moveLearn.hidden=true}
function showMoves(){if(battleState.busy||battleState.over)return;renderMoves();battleCommand.hidden=true;battleMoves.hidden=false;moveLearn.hidden=true;battleMessage.textContent='どの技を つかう？'}
function battleText(text,delay=720){battleMessage.textContent=text;return new Promise(resolve=>setTimeout(resolve,delay))}
function animateOnce(target,name){target.classList.remove(name);void target.offsetWidth;target.classList.add(name);setTimeout(()=>target.classList.remove(name),460)}
function battleHit(target){animateOnce(target,'hit')}
function battleAttack(target){animateOnce(target,'attack')}
function damage(min,max){return min+Math.floor(Math.random()*(max-min+1))}

function showMoveReplacement(newMoveId){
  profile.pendingMove=newMoveId;saveProfile();battleCommand.hidden=true;battleMoves.hidden=true;moveLearn.hidden=false;moveLearn.replaceChildren();
  const title=document.createElement('p');title.textContent=`${MOVE_DATA[newMoveId].name}を覚える。忘れる技を選んでください。`;moveLearn.append(title);
  profile.moves.forEach((oldId,index)=>{const button=document.createElement('button');button.type='button';button.textContent=`${MOVE_DATA[oldId].name}と交換`;button.addEventListener('click',()=>{profile.moves[index]=newMoveId;profile.pendingMove=null;saveProfile();moveLearn.hidden=true;battleMessage.textContent=`${MOVE_DATA[newMoveId].name}を おぼえた！`});moveLearn.append(button)});
  const cancel=document.createElement('button');cancel.type='button';cancel.textContent='今は覚えない';cancel.addEventListener('click',()=>{profile.pendingMove=null;saveProfile();moveLearn.hidden=true;battleMessage.textContent='技を覚えずに終えた'});moveLearn.append(cancel);
}
async function awardExperience(){
  const gained=40;profile.xp+=gained;await battleText(`経験値を ${gained} かくとく！`);let learned=null,evolved=false;
  while(profile.xp>=xpNeeded()){
    profile.xp-=xpNeeded();profile.level+=1;await battleText(`イグニスは Lv.${profile.level}に あがった！`);
    if(LEARN_LEVELS[profile.level])learned=LEARN_LEVELS[profile.level];
    if(profile.level>=10&&profile.stage===1){profile.stage=2;evolved=true}
  }
  saveProfile();updateBattleHp();
  if(evolved)await battleText('イグニスに 進化の力が めばえた！');
  if(learned){if(profile.moves.length<4){profile.moves.push(learned);saveProfile();await battleText(`${MOVE_DATA[learned].name}を おぼえた！`)}else showMoveReplacement(learned)}
}

async function useMove(name){
  if(battleState.busy||battleState.over)return;battleState.busy=true;battleMoves.hidden=true;
  const move=MOVE_DATA[name];
  if(!move){battleState.busy=false;return}
  if(move.guard){
    battleState.guard=true;battleAttack(playerBattler);await battleText('イグニスは ほのおのまもりを まとった！');
  }else{
    const multiplier=typeMultiplier(move.type,'water');battleAttack(playerBattler);await battleText(`イグニスの ${move.name}！`,480);
    battleHit(enemyBattler);battleState.enemy-=Math.max(1,Math.round((damage(...move.power)+Math.floor((profile.level-5)/2))*multiplier));updateBattleHp();
    await battleText(multiplier>1?'効果は ばつぐんだ！':multiplier<1?'効果は いまひとつ…':'アクアロに ダメージ！');
  }
  if(battleState.enemy<=0){battleState.over=true;await battleText('アクアロは たおれた！');battle.classList.add('battle-won');await awardExperience();if(!profile.pendingMove)battleMessage.textContent='イグニスの かち！　画面をタップして再戦';battleState.busy=false;return}
  const enemyMove=Math.random()<.68?{name:'みずでっぽう',type:'water',power:[4,6]}:{name:'たいあたり',type:'normal',power:[3,5]};
  battleAttack(enemyBattler);await battleText(`アクアロの ${enemyMove.name}！`,480);
  const multiplier=typeMultiplier(enemyMove.type,'fire');battleHit(playerBattler);let hit=Math.max(1,Math.round(damage(...enemyMove.power)*multiplier));if(battleState.guard){hit=Math.max(1,Math.floor(hit/2));battleState.guard=false}
  battleState.player-=hit;updateBattleHp();await battleText(multiplier>1?'効果は ばつぐんだ！':multiplier<1?'効果は いまひとつ…':'イグニスに ダメージ！');
  if(battleState.player<=0){battleState.over=true;await battleText('イグニスは たおれた！');battleMessage.textContent='アクアロの かち！　画面をタップして再戦';battle.classList.add('battle-lost')}
  else{battleMessage.textContent='イグニスは どうする？';showCommands()}
  battleState.busy=false;
}
function startBattle(){
  auto=false;manual=null;target={x,y};const maxHp=24+(profile.level-5)*4;battleState={player:maxHp,playerMax:maxHp,enemy:24,busy:false,guard:false,over:false};
  battle.classList.remove('battle-won','battle-lost');battle.hidden=false;updateBattleHp();showCommands();
  battleMessage.textContent='アクアロが あらわれた！';
  drawBattleSprite(playerBattler,monsters.fire.thumb,1);drawBattleSprite(enemyBattler,monsters.water.thumb,0);
  setTimeout(()=>{if(!battleState.busy&&!battleState.over)battleMessage.textContent='イグニスは どうする？'},800);
}
function closeBattle(){battle.hidden=true}
document.querySelector('#battle-close').addEventListener('click',closeBattle);
document.querySelector('#move-back').addEventListener('click',()=>{battleMessage.textContent='イグニスは どうする？';showCommands()});
document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>{
  if(button.dataset.command==='fight'){showMoves();return}
  if(button.dataset.command==='run'){closeBattle();return}
  battleMessage.textContent=button.dataset.command==='party'?'交代できる仲間は まだいない！':'どうぐは まだ持っていない！';
}));
battleMessage.addEventListener('click',()=>{if(battleState.over&&!profile.pendingMove)startBattle()});
[playerBattler,enemyBattler].forEach(target=>target.addEventListener('animationend',()=>target.classList.remove('hit','attack')));
const requestedMonster=new URLSearchParams(location.search).get('monster');
setMonster(monsters[requestedMonster]?requestedMonster:(localStorage.getItem('walkLabMonster')||'fire'));
chooseTarget(.25,.7);requestAnimationFrame(tick);
